fn main() {
    if let Err(error) = aimux_lib::run_gateway() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
