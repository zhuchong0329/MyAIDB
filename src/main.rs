use std::process::ExitCode;

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);

    match args.next().as_deref() {
        None => {
            println!("{}", myaidb::project_identity());
            ExitCode::SUCCESS
        }
        Some("-h" | "--help") => {
            print_help();
            ExitCode::SUCCESS
        }
        Some("-V" | "--version") => {
            println!("{}", myaidb::project_identity());
            ExitCode::SUCCESS
        }
        Some(flag) => {
            eprintln!("unknown argument: {flag}");
            eprintln!("try `myaidb --help`");
            ExitCode::from(2)
        }
    }
}

fn print_help() {
    println!("{}", myaidb::project_identity());
    println!();
    println!("Usage: myaidb [OPTIONS]");
    println!();
    println!("Options:");
    println!("  -h, --help       Print help");
    println!("  -V, --version    Print version");
}
