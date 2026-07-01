use std::io::Write;
use std::process::{Command, Stdio};

#[test]
fn library_identity_is_available() {
    assert_eq!(myaidb::PROJECT_NAME, "MyAIDB");
    assert_eq!(myaidb::project_identity(), "MyAIDB 0.1.0");
}

#[test]
fn binary_prints_help() {
    let output = Command::new(env!("CARGO_BIN_EXE_myaidb"))
        .arg("--help")
        .output()
        .expect("myaidb binary should run");

    assert!(output.status.success());

    let stdout = String::from_utf8(output.stdout).expect("stdout should be valid UTF-8");
    assert!(stdout.contains("MyAIDB 0.1.0"));
    assert!(stdout.contains("Usage: myaidb [OPTIONS] [repl]"));
    assert!(stdout.contains("repl"));
}

#[test]
fn binary_runs_repl_workflow_from_stdin() {
    let mut child = Command::new(env!("CARGO_BIN_EXE_myaidb"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("myaidb binary should run");

    {
        let stdin = child.stdin.as_mut().expect("stdin should be piped");
        stdin
            .write_all(
                b"create table users (id integer, name text);
insert into users values (1, 'Ada');
select * from users;
show tables;
.schema users;
.quit
",
            )
            .expect("stdin write should work");
    }

    let output = child.wait_with_output().expect("myaidb binary should exit");

    assert!(output.status.success());

    let stdout = String::from_utf8(output.stdout).expect("stdout should be valid UTF-8");
    assert!(stdout.contains("created table users"));
    assert!(stdout.contains("inserted 1 row into users"));
    assert!(stdout.contains("id | name"));
    assert!(stdout.contains("1  | Ada"));
    assert!(stdout.contains("tables"));
    assert!(stdout.contains("users"));
    assert!(stdout.contains("table: users"));
    assert!(stdout.contains("2 | name"));
    assert!(stdout.contains("Text"));
    assert!(stdout.contains("bye"));
}
