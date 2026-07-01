use std::io::IsTerminal;
use std::process::ExitCode;

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);

    match args.next().as_deref() {
        None => run_repl(),
        Some("--seed") => {
            let Some(seed_path) = args.next() else {
                eprintln!("missing seed file after --seed");
                return ExitCode::from(2);
            };
            if let Some(extra) = args.next() {
                eprintln!("unexpected argument after seed file: {extra}");
                return ExitCode::from(2);
            }
            run_seeded_repl(&seed_path)
        }
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
    let mut catalog = myaidb::Catalog::new();
    run_repl_with_catalog(&mut catalog)
}

fn run_seeded_repl(seed_path: &str) -> ExitCode {
    let seed_file = match std::fs::File::open(seed_path) {
        Ok(file) => file,
        Err(error) => {
            eprintln!("failed to open seed file `{seed_path}`: {error}");
            return ExitCode::from(1);
        }
    };
    let mut catalog = myaidb::Catalog::new();

    println!("loading seed data from {seed_path}");
    let commands_loaded =
        match myaidb::cli::run_seed_script(&mut catalog, std::io::BufReader::new(seed_file)) {
            Ok(count) => count,
            Err(error) => {
                eprintln!("failed to load seed data: {error}");
                return ExitCode::from(1);
            }
        };
    println!("seed data loaded ({commands_loaded} commands)");

    run_repl_with_catalog(&mut catalog)
}

fn run_repl_with_catalog(catalog: &mut myaidb::Catalog) -> ExitCode {
    let stdin = std::io::stdin();
    let mut stdout = std::io::stdout();

    let result = if stdin.is_terminal() && stdout.is_terminal() {
        myaidb::cli::run_interactive_repl_with_catalog(catalog, &mut stdout)
    } else {
        myaidb::cli::run_repl_with_catalog(catalog, stdin.lock(), &mut stdout)
    };

    match result {
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
    println!("      --seed FILE  Load SQL seed data before starting the CLI");
    println!("  -h, --help       Print help");
    println!("  -V, --version    Print version");
}
