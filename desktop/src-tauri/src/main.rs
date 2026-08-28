// 紫微斗数桌面壳：启动内嵌 FastAPI sidecar 后加载前端。
//
// MVP：直接以项目 venv 的 python 启动 uvicorn。
// 生产化路径（Phase 2+）：PyInstaller 打包 sidecar 二进制，经 tauri sidecar 机制加载。

use parking_lot::Mutex;
use std::process::{Child, Command};

static SIDECAR: Mutex<Option<Child>> = Mutex::new(None);

fn project_root() -> std::path::PathBuf {
    // dev: desktop/src-tauri → 上两级为项目根；打包后由安装布局决定
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn start_sidecar() -> Option<Child> {
    let root = project_root();
    let python = root.join(".venv/bin/python");
    let child = Command::new(python)
        .args(["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765"])
        .env("PYTHONPATH", "engine:server")
        .current_dir(&root)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .ok();
    // 等 sidecar 就绪（最长 15s），避免 webview 首屏请求打到未启动的服务
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(15);
    while std::time::Instant::now() < deadline {
        if std::net::TcpStream::connect("127.0.0.1:8765").is_ok() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }
    child
}

fn main() {
    let app = tauri::Builder::default()
        // 导出保存对话框 / 写文件 / 剪贴板（权限见 capabilities/main.json）
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .setup(|_app| {
            *SIDECAR.lock() = start_sidecar();
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|_app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(mut child) = SIDECAR.lock().take() {
                let _ = child.kill();
            }
        }
    });
}
