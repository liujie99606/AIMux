use std::{
    fs::OpenOptions,
    io::{self, Write},
    path::PathBuf,
};

use tracing_subscriber::{fmt, fmt::MakeWriter, EnvFilter};

use crate::config::Settings;

pub fn init() {
    let log_dir = Settings::data_dir().join("log");
    if let Err(error) = std::fs::create_dir_all(&log_dir) {
        eprintln!("创建日志目录失败 ({}): {error}", log_dir.display());
        fmt().with_env_filter(default_filter()).init();
        return;
    }

    fmt()
        .with_env_filter(default_filter())
        .with_writer(DailyFileWriter {
            directory: log_dir.clone(),
        })
        .with_ansi(false)
        .init();
    tracing::info!(log_directory = %log_dir.display(), "日志已初始化");
}

fn default_filter() -> EnvFilter {
    EnvFilter::new("aimux_lib=info")
}

#[derive(Clone)]
struct DailyFileWriter {
    directory: PathBuf,
}

impl<'a> MakeWriter<'a> for DailyFileWriter {
    type Writer = Box<dyn Write + Send>;

    fn make_writer(&'a self) -> Self::Writer {
        let filename = format!("aimux-{}.log", chrono::Local::now().format("%Y-%m-%d"));
        let path = self.directory.join(filename);
        match OpenOptions::new().create(true).append(true).open(path) {
            Ok(file) => Box::new(file),
            Err(error) => {
                eprintln!("打开日志文件失败: {error}");
                Box::new(io::stderr())
            }
        }
    }
}
