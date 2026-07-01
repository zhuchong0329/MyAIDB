use std::process::ExitCode;

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);

    match args.next().as_deref() {
        None => run_repl(),
        Some("repl") => {
            if let Some(extra) = args.next() {
                eprintln!("unexpected argument after repl: {extra}");
                return ExitCode::from(2);
            }
            run_repl()
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

fn run_repl() -> ExitCode {
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();

    match myaidb::cli::run_repl(stdin.lock(), &mut stdout) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("io error: {error}");
            ExitCode::from(1)
        }
    }
}

fn print_help() {
    println!("{}", myaidb::project_identity());
    println!();
    println!("Usage: myaidb [OPTIONS] [repl]");
    println!();
    println!("Commands:");
    println!("  repl             Start interactive in-memory CLI");
    println!();
    println!("Options:");
    println!("  -h, --help       Print help");
    println!("  -V, --version    Print version");
}
