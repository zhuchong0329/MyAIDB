use std::process::Command;

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
    assert!(stdout.contains("Usage: myaidb [OPTIONS]"));
}
