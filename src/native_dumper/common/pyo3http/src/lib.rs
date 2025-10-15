use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyList};
use reqwest::{Client, Response, header::{HeaderMap, HeaderName, HeaderValue}};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tokio::runtime::Runtime;

#[pyclass]
struct HttpResponse {
    response: Arc<Mutex<Option<Response>>>,
    buffer: Arc<Mutex<Vec<u8>>>,
    position: Arc<Mutex<u64>>,
    is_complete: Arc<Mutex<bool>>,
    rt: Arc<Runtime>,
    status_code: Arc<Mutex<Option<u16>>>,
    headers: Arc<Mutex<Option<HashMap<String, String>>>>,
    content_length: Arc<Mutex<Option<u64>>>,
    first_read_data: Arc<Mutex<Option<Vec<u8>>>>,
    seek_allowed: Arc<Mutex<bool>>,
    has_used_seek: Arc<Mutex<bool>>,
}

impl HttpResponse {
    fn is_reading_complete(&self) -> bool {
        let complete_guard = self.is_complete.lock().unwrap();
        *complete_guard
    }

    fn set_complete(&self) {
        let mut complete_guard = self.is_complete.lock().unwrap();
        *complete_guard = true;
    }

    fn internal_close(&self) {
        let mut response_guard = self.response.lock().unwrap();
        let mut buffer_guard = self.buffer.lock().unwrap();
        let mut first_read_data_guard = self.first_read_data.lock().unwrap();
        *response_guard = None;
        buffer_guard.clear();
        *first_read_data_guard = None;
    }

    async fn read_chunk(response: &mut Response) -> Result<Option<Vec<u8>>, reqwest::Error> {
        match response.chunk().await {
            Ok(Some(chunk)) => Ok(Some(chunk.to_vec())),
            Ok(None) => Ok(None),
            Err(e) => Err(e),
        }
    }

    fn initialize_metadata(&self) {
        let response_guard = self.response.lock().unwrap();
        if let Some(ref resp) = *response_guard {
            {
                let mut status_guard = self.status_code.lock().unwrap();
                *status_guard = Some(resp.status().as_u16());
            }

            {
                let mut headers_guard = self.headers.lock().unwrap();
                let mut headers_map = HashMap::new();
                for (key, value) in resp.headers() {
                    if let Ok(value_str) = value.to_str() {
                        headers_map.insert(key.as_str().to_lowercase(), value_str.to_string());
                    }
                }
                *headers_guard = Some(headers_map);
            }

            {
                let mut content_length_guard = self.content_length.lock().unwrap();
                *content_length_guard = resp.content_length();
            }
        }
    }

    fn from_response(response: Response, rt: Arc<Runtime>) -> Self {
        let response_obj = Self {
            response: Arc::new(Mutex::new(Some(response))),
            buffer: Arc::new(Mutex::new(Vec::new())),
            position: Arc::new(Mutex::new(0)),
            is_complete: Arc::new(Mutex::new(false)),
            rt: rt.clone(),
            status_code: Arc::new(Mutex::new(None)),
            headers: Arc::new(Mutex::new(None)),
            content_length: Arc::new(Mutex::new(None)),
            first_read_data: Arc::new(Mutex::new(None)),
            seek_allowed: Arc::new(Mutex::new(false)),
            has_used_seek: Arc::new(Mutex::new(false)),
        };

        response_obj.initialize_metadata();
        response_obj
    }
}

#[pymethods]
impl HttpResponse {

    fn read(&self, py: Python, size: Option<usize>) -> PyResult<Py<PyBytes>> {
        if self.is_reading_complete() {
            return Ok(PyBytes::new(py, &[]).into());
        }

        if let Some(1) = size {
            return self.read1(py);
        }

        let rt = self.rt.clone();
        let response = self.response.clone();
        let buffer = self.buffer.clone();
        let position = self.position.clone();
        let is_complete = self.is_complete.clone();
        let first_read_data = self.first_read_data.clone();
        let seek_allowed = self.seek_allowed.clone();
        let data: Vec<u8> = py.allow_threads(move || {
            rt.block_on(async {
                let mut response_guard = response.lock().unwrap();
                let mut buffer_guard = buffer.lock().unwrap();
                let mut pos_guard = position.lock().unwrap();

                if *is_complete.lock().unwrap() {
                    return Vec::new();
                }

                if let Some(ref mut resp) = *response_guard {
                    let target_size = size.unwrap_or(usize::MAX);
                    let mut collected_data = Vec::new();

                    if !buffer_guard.is_empty() {
                        if buffer_guard.len() <= target_size {
                            collected_data = std::mem::take(&mut *buffer_guard);
                        } else {
                            collected_data = buffer_guard.drain(..target_size).collect();
                        }
                    }

                    if collected_data.len() < target_size {
                        let remaining_needed = target_size - collected_data.len();

                        if target_size == usize::MAX {
                            loop {
                                match Self::read_chunk(resp).await {
                                    Ok(Some(chunk_data)) => {
                                        collected_data.extend_from_slice(&chunk_data);
                                    }
                                    Ok(None) => {
                                        *is_complete.lock().unwrap() = true;
                                        break;
                                    }
                                    Err(_) => {
                                        *is_complete.lock().unwrap() = true;
                                        break;
                                    }
                                }
                            }
                        } else {
                            let mut remaining = remaining_needed;

                            while remaining > 0 {
                                match Self::read_chunk(resp).await {
                                    Ok(Some(chunk_data)) => {
                                        if chunk_data.len() > remaining {
                                            collected_data.extend_from_slice(&chunk_data[..remaining]);
                                            buffer_guard.extend_from_slice(&chunk_data[remaining..]);
                                            break;
                                        } else {
                                            collected_data.extend_from_slice(&chunk_data);
                                            remaining -= chunk_data.len();
                                        }
                                    }
                                    Ok(None) => {
                                        *is_complete.lock().unwrap() = true;
                                        break;
                                    }
                                    Err(_) => {
                                        *is_complete.lock().unwrap() = true;
                                        break;
                                    }
                                }
                            }
                        }
                    }

                    let should_save_first_read = {
                        let first_read_data_guard = first_read_data.lock().unwrap();
                        first_read_data_guard.is_none() && !collected_data.is_empty()
                    };

                    if should_save_first_read {
                        let mut first_read_data_guard = first_read_data.lock().unwrap();
                        let mut seek_allowed_guard = seek_allowed.lock().unwrap();
                        *first_read_data_guard = Some(collected_data.clone());
                        *seek_allowed_guard = true;
                    }

                    *pos_guard += collected_data.len() as u64;
                    collected_data
                } else {
                    *is_complete.lock().unwrap() = true;
                    Vec::new()
                }
            })
        });

        Ok(PyBytes::new(py, &data).into())
    }

    fn read1(&self, py: Python) -> PyResult<Py<PyBytes>> {
        if self.is_reading_complete() {
            return Ok(PyBytes::new(py, &[]).into());
        }

        let rt = self.rt.clone();
        let response = self.response.clone();
        let buffer = self.buffer.clone();
        let position = self.position.clone();
        let is_complete = self.is_complete.clone();
        let first_read_data = self.first_read_data.clone();
        let seek_allowed = self.seek_allowed.clone();
        let data: Vec<u8> = py.allow_threads(move || {
            rt.block_on(async {
                let mut response_guard = response.lock().unwrap();
                let mut buffer_guard = buffer.lock().unwrap();
                let mut pos_guard = position.lock().unwrap();
                
                if *is_complete.lock().unwrap() {
                    return Vec::new();
                }

                if let Some(ref mut resp) = *response_guard {
                    let result_byte = if !buffer_guard.is_empty() {
                        let byte = buffer_guard.remove(0);
                        Some(byte)
                    } else {
                        match Self::read_chunk(resp).await {
                            Ok(Some(chunk_data)) => {
                                if !chunk_data.is_empty() {
                                    let byte = chunk_data[0];
                                    if chunk_data.len() > 1 {
                                        buffer_guard.extend_from_slice(&chunk_data[1..]);
                                    }
                                    Some(byte)
                                } else {
                                    None
                                }
                            }
                            Ok(None) => {
                                *is_complete.lock().unwrap() = true;
                                None
                            }
                            Err(_) => {
                                *is_complete.lock().unwrap() = true;
                                None
                            }
                        }
                    };

                    if let Some(byte) = result_byte {
                        let should_save_first_read = {
                            let first_read_data_guard = first_read_data.lock().unwrap();
                            first_read_data_guard.is_none()
                        };

                        if should_save_first_read {
                            let mut first_read_data_guard = first_read_data.lock().unwrap();
                            let mut seek_allowed_guard = seek_allowed.lock().unwrap();
                            *first_read_data_guard = Some(vec![byte]);
                            *seek_allowed_guard = true;
                        }

                        *pos_guard += 1;
                        vec![byte]
                    } else {
                        Vec::new()
                    }
                } else {
                    *is_complete.lock().unwrap() = true;
                    Vec::new()
                }
            })
        });

        Ok(PyBytes::new(py, &data).into())
    }

    fn get_status(&self) -> PyResult<Option<u16>> {
        let status_guard = self.status_code.lock().unwrap();
        Ok(*status_guard)
    }

    fn get_headers(&self) -> PyResult<Option<HashMap<String, String>>> {
        let headers_guard = self.headers.lock().unwrap();
        Ok(headers_guard.clone())
    }

    fn get_header(&self, name: String) -> PyResult<Option<String>> {
        let headers_guard = self.headers.lock().unwrap();
        if let Some(ref headers) = *headers_guard {
            Ok(headers.get(&name.to_lowercase()).cloned())
        } else {
            Ok(None)
        }
    }

    fn get_content_length(&self) -> PyResult<Option<u64>> {
        let content_length_guard = self.content_length.lock().unwrap();
        Ok(*content_length_guard)
    }

    fn is_success(&self) -> PyResult<bool> {
        let status_guard = self.status_code.lock().unwrap();
        if let Some(status) = *status_guard {
            Ok(status >= 200 && status < 300)
        } else {
            Ok(false)
        }
    }

    fn is_redirect(&self) -> PyResult<bool> {
        let status_guard = self.status_code.lock().unwrap();
        if let Some(status) = *status_guard {
            Ok(status >= 300 && status < 400)
        } else {
            Ok(false)
        }
    }

    fn is_client_error(&self) -> PyResult<bool> {
        let status_guard = self.status_code.lock().unwrap();
        if let Some(status) = *status_guard {
            Ok(status >= 400 && status < 500)
        } else {
            Ok(false)
        }
    }

    fn is_server_error(&self) -> PyResult<bool> {
        let status_guard = self.status_code.lock().unwrap();
        if let Some(status) = *status_guard {
            Ok(status >= 500 && status < 600)
        } else {
            Ok(false)
        }
    }

    fn get_content_type(&self) -> PyResult<Option<String>> {
        self.get_header("content-type".to_string())
    }

    fn get_url(&self) -> PyResult<Option<String>> {
        let response_guard = self.response.lock().unwrap();
        if let Some(ref resp) = *response_guard {
            Ok(Some(resp.url().to_string()))
        } else {
            Ok(None)
        }
    }

    fn seek(&self, pos: u64) -> PyResult<()> {
        if pos == 0 {
            let (is_seek_allowed, has_first_data) = {
                let seek_allowed_guard = self.seek_allowed.lock().unwrap();
                let has_used_seek_guard = self.has_used_seek.lock().unwrap();
                let first_read_data_guard = self.first_read_data.lock().unwrap();
                
                (
                    *seek_allowed_guard && !*has_used_seek_guard,
                    first_read_data_guard.is_some()
                )
            };

            if !is_seek_allowed {
                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                    "Seek to position 0 is allowed only once after first read"
                ));
            }

            if !has_first_data {
                return Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                    "No data has been read yet, cannot seek to position 0"
                ));
            }

            let first_read_data_guard = self.first_read_data.lock().unwrap();
            if let Some(ref first_data) = *first_read_data_guard {
                let mut position = self.position.lock().unwrap();
                let mut buffer = self.buffer.lock().unwrap();
                let mut complete = self.is_complete.lock().unwrap();
                let mut has_used_seek_guard = self.has_used_seek.lock().unwrap();

                buffer.clear();
                buffer.extend_from_slice(first_data);
                *position = 0;
                *complete = false;
                *has_used_seek_guard = true;
                
                Ok(())
            } else {
                Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                    "No data has been read yet, cannot seek to position 0"
                ))
            }
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                "Seek is only supported to position 0 for HTTP streams"
            ))
        }
    }

    fn seekable(&self) -> PyResult<bool> {
        let seek_allowed_guard = self.seek_allowed.lock().unwrap();
        let has_used_seek_guard = self.has_used_seek.lock().unwrap();

        Ok(*seek_allowed_guard && !*has_used_seek_guard)
    }

    fn close(&self) -> PyResult<()> {
        self.internal_close();
        self.set_complete();
        Ok(())
    }

    fn is_closed(&self) -> PyResult<bool> {
        Ok(self.is_reading_complete())
    }

    fn get_info(&self) -> PyResult<HashMap<String, String>> {
        let mut info = HashMap::new();

        if let Some(status) = self.get_status()? {
            info.insert("status".to_string(), status.to_string());
            info.insert("status_text".to_string(), if self.is_success()? { "OK".to_string() } else { "Error".to_string() });
        }

        if let Some(length) = self.get_content_length()? {
            info.insert("content_length".to_string(), length.to_string());
        }

        if let Some(content_type) = self.get_content_type()? {
            info.insert("content_type".to_string(), content_type);
        }

        if let Some(url) = self.get_url()? {
            info.insert("url".to_string(), url);
        }

        let position = self.tell()?;
        info.insert("bytes_read".to_string(), position.to_string());

        info.insert("closed".to_string(), self.is_closed()?.to_string());
        info.insert("complete".to_string(), self.is_reading_complete().to_string());

        let seek_allowed = self.seek_allowed.lock().unwrap();
        let has_used_seek = self.has_used_seek.lock().unwrap();
        let first_read_data = self.first_read_data.lock().unwrap();

        info.insert("seek_allowed".to_string(), (*seek_allowed).to_string());
        info.insert("seek_used".to_string(), (*has_used_seek).to_string());
        info.insert("has_first_read_data".to_string(), first_read_data.is_some().to_string());

        let seekable = *seek_allowed && !*has_used_seek;
        info.insert("seekable".to_string(), seekable.to_string());

        if let Some(ref data) = *first_read_data {
            info.insert("first_read_size".to_string(), data.len().to_string());
        }

        Ok(info)
    }

    fn tell(&self) -> PyResult<u64> {
        let position = self.position.lock().unwrap();
        Ok(*position)
    }
}

impl Clone for HttpResponse {
    fn clone(&self) -> Self {
        Self {
            response: self.response.clone(),
            buffer: self.buffer.clone(),
            position: self.position.clone(),
            is_complete: self.is_complete.clone(),
            rt: self.rt.clone(),
            status_code: self.status_code.clone(),
            headers: self.headers.clone(),
            content_length: self.content_length.clone(),
            first_read_data: self.first_read_data.clone(),
            seek_allowed: self.seek_allowed.clone(),
            has_used_seek: self.has_used_seek.clone(),
        }
    }
}

#[pyclass]
struct HttpSession {
    client: Client,
    rt: Arc<Runtime>,
}

#[pymethods]
impl HttpSession {
    #[new]
    fn new(timeout: Option<f64>) -> PyResult<Self> {
        let client_builder = Client::builder()
            .tcp_keepalive(Duration::from_secs(60))
            .pool_max_idle_per_host(10);

        let client = if let Some(timeout_secs) = timeout {
            client_builder
                .timeout(Duration::from_secs_f64(timeout_secs))
                .build()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create HTTP client: {}", e)
                ))?
        } else {
            client_builder
                .timeout(Duration::from_secs(30))
                .build()
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to create HTTP client: {}", e)
                ))?
        };

        let rt = Arc::new(Runtime::new().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to create runtime: {}", e))
        })?);

        Ok(HttpSession { client, rt })
    }

    fn post(
        &self,
        py: Python,
        url: String,
        headers: Option<HashMap<String, String>>,
        params: Option<HashMap<String, String>>,
        data: Option<Bound<'_, PyAny>>,
        timeout: Option<f64>,
    ) -> PyResult<HttpResponse> {
        let client = self.client.clone();
        let rt = self.rt.clone();
        let mut header_map = HeaderMap::new();

        if let Some(headers) = headers {
            for (key, value) in headers {
                if let Ok(header_name) = key.parse::<HeaderName>() {
                    if let Ok(header_value) = value.parse::<HeaderValue>() {
                        header_map.insert(header_name, header_value);
                    }
                }
            }
        }

        let mut request_builder = client.post(&url).headers(header_map);

        if let Some(params) = params {
            request_builder = request_builder.query(&params);
        }

        if let Some(timeout_secs) = timeout {
            request_builder = request_builder.timeout(Duration::from_secs_f64(timeout_secs));
        }

        if let Some(data_obj) = data {
            let data_bytes = if let Ok(bytes) = data_obj.downcast::<PyBytes>() {
                bytes.as_bytes().to_vec()
            } else if let Ok(list) = data_obj.downcast::<PyList>() {
                let mut result = Vec::new();
                for (idx, item) in list.iter().enumerate() {
                    if let Ok(bytes) = item.downcast::<PyBytes>() {
                        result.extend_from_slice(bytes.as_bytes());
                    } else if let Ok(vec_bytes) = item.extract::<Vec<u8>>() {
                        result.extend_from_slice(&vec_bytes);
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                            format!("List element at index {} must be bytes or byte array", idx)
                        ));
                    }
                }
                result
            } else if let Ok(bytes_vec) = data_obj.extract::<Vec<u8>>() {
                bytes_vec
            } else {
                let mut result = Vec::new();
                let iter = data_obj.getattr("__iter__")?;
                let iterator = iter.call0()?;
                
                loop {
                    let next_result = iterator.call_method0("__next__");
                    match next_result {
                        Ok(item) => {
                            if let Ok(bytes) = item.downcast::<PyBytes>() {
                                result.extend_from_slice(bytes.as_bytes());
                            } else if let Ok(vec_bytes) = item.extract::<Vec<u8>>() {
                                result.extend_from_slice(&vec_bytes);
                            } else if let Ok(byte_array) = item.extract::<[u8; 1]>() {
                                result.extend_from_slice(&byte_array);
                            } else if let Ok(byte) = item.extract::<u8>() {
                                result.push(byte);
                            } else {
                                return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                                    "Iterator yielded unsupported type, expected bytes, bytearray, or u8"
                                ));
                            }
                        }
                        Err(e) => {
                            if e.is_instance_of::<pyo3::exceptions::PyStopIteration>(py) {
                                break;
                            } else {
                                return Err(PyErr::new::<pyo3::exceptions::PyTypeError, _>(
                                    format!("Error during iteration: {}", e)
                                ));
                            }
                        }
                    }
                }

                result
            };

            request_builder = request_builder.body(data_bytes);
        } else {
            request_builder = request_builder.header("Content-Length", "0");
        }

        let response = rt.block_on(async {
            request_builder.send().await
        });

        match response {
            Ok(resp) => {
                let response_obj = HttpResponse::from_response(resp, rt.clone());
                Ok(response_obj)
            }
            Err(e) => Err(PyErr::new::<pyo3::exceptions::PyIOError, _>(
                format!("HTTP request failed: {}", e)
            )),
        }
    }

    fn post_stream(
        &self,
        py: Python,
        url: String,
        headers: Option<HashMap<String, String>>,
        params: Option<HashMap<String, String>>,
        data: Option<Bound<'_, PyAny>>,
        timeout: Option<f64>,
    ) -> PyResult<HttpResponse> {
        self.post(py, url, headers, params, data, timeout)
    }

    fn close(&mut self) {
        if let Ok(rt) = Arc::try_unwrap(std::mem::replace(&mut self.rt, Arc::new(Runtime::new().unwrap()))) {
            rt.shutdown_background();
        }
        let _ = std::mem::replace(&mut self.client, Client::new());
    }
}

#[pymodule]
fn pyo3http(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<HttpSession>()?;
    m.add_class::<HttpResponse>()?;
    Ok(())
}
