use std::io::{self, BufRead, Write};

use rustyline::error::ReadlineError;
use rustyline::DefaultEditor;

use crate::{execute_sql, Catalog, Column, ExecuteError, ExecuteResult, Row, Value};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommandFlow {
    Continue,
    Quit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SchemaCommand<'a> {
    All,
    Table(&'a str),
    InvalidUsage,
}

pub fn run_repl<R, W>(mut reader: R, writer: &mut W) -> io::Result<()>
where
    R: BufRead,
    W: Write,
{
    let mut catalog = Catalog::new();
    run_repl_with_catalog(&mut catalog, &mut reader, writer)
}

pub fn run_repl_with_catalog<R, W>(
    catalog: &mut Catalog,
    mut reader: R,
    writer: &mut W,
) -> io::Result<()>
where
    R: BufRead,
    W: Write,
{
    let mut pending = String::new();
    let mut line = String::new();

    writeln!(writer, "{}", crate::project_identity())?;
    writeln!(writer, "type .help for help, .quit to exit")?;

    loop {
        if pending.is_empty() {
            write!(writer, "myaidb> ")?;
        } else {
            write!(writer, "   ...> ")?;
        }
        writer.flush()?;

        line.clear();
        let bytes_read = reader.read_line(&mut line)?;
        if bytes_read == 0 {
            if !pending.trim().is_empty() {
                process_command(catalog, pending.trim(), writer)?;
            }
            break;
        }

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        if !pending.is_empty() {
            pending.push(' ');
        }
        pending.push_str(trimmed);

        if !is_complete_command(&pending) {
            continue;
        }

        let flow = process_command(catalog, pending.trim(), writer)?;
        pending.clear();

        if flow == CommandFlow::Quit {
            break;
        }
    }

    Ok(())
}

pub fn run_interactive_repl<W>(writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let mut catalog = Catalog::new();
    run_interactive_repl_with_catalog(&mut catalog, writer)
}

pub fn run_interactive_repl_with_catalog<W>(catalog: &mut Catalog, writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let mut editor = DefaultEditor::new().map_err(to_io_error)?;
    let mut pending = String::new();

    writeln!(writer, "{}", crate::project_identity())?;
    writeln!(writer, "type .help for help, .quit to exit")?;

    loop {
        let prompt = if pending.is_empty() {
            "myaidb> "
        } else {
            "   ...> "
        };
        let line = match editor.readline(prompt) {
            Ok(line) => line,
            Err(ReadlineError::Interrupted | ReadlineError::Eof) => {
                writeln!(writer, "bye")?;
                break;
            }
            Err(error) => return Err(to_io_error(error)),
        };
        let trimmed = line.trim();

        if trimmed.is_empty() {
            continue;
        }

        if !pending.is_empty() {
            pending.push(' ');
        }
        pending.push_str(trimmed);

        if !is_complete_command(&pending) {
            continue;
        }

        let completed_command = pending.trim().to_string();
        let flow = process_command(catalog, &completed_command, writer)?;
        if flow == CommandFlow::Continue {
            let _ = editor.add_history_entry(completed_command.as_str());
        }
        pending.clear();

        if flow == CommandFlow::Quit {
            break;
        }
    }

    Ok(())
}

pub fn run_seed_script<R>(catalog: &mut Catalog, mut reader: R) -> io::Result<usize>
where
    R: BufRead,
{
    let mut pending = String::new();
    let mut line = String::new();
    let mut commands_loaded = 0;

    loop {
        line.clear();
        let bytes_read = reader.read_line(&mut line)?;
        if bytes_read == 0 {
            if !pending.trim().is_empty() {
                execute_seed_command(catalog, pending.trim())?;
                commands_loaded += 1;
            }
            break;
        }

        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with("--") {
            continue;
        }

        if !pending.is_empty() {
            pending.push(' ');
        }
        pending.push_str(trimmed);

        if !is_complete_command(&pending) {
            continue;
        }

        execute_seed_command(catalog, pending.trim())?;
        commands_loaded += 1;
        pending.clear();
    }

    Ok(commands_loaded)
}

fn execute_seed_command(catalog: &mut Catalog, command: &str) -> io::Result<()> {
    execute_sql(catalog, command).map(|_| ()).map_err(|error| {
        io::Error::other(format!(
            "seed command `{}` failed: {}",
            normalize_command(command),
            format_execute_error(&error)
        ))
    })
}

fn to_io_error(error: ReadlineError) -> io::Error {
    io::Error::other(error)
}

fn is_complete_command(command: &str) -> bool {
    let trimmed = command.trim();
    let normalized = normalize_command(trimmed);

    is_meta_command(normalized)
        || is_show_tables_command(normalized)
        || parse_schema_command(normalized).is_some()
        || trimmed.ends_with(';')
        || looks_like_complete_sql(normalized)
}

fn looks_like_complete_sql(normalized: &str) -> bool {
    (normalized.starts_with("select ") && normalized.contains(" from "))
        || (normalized.starts_with("insert ") && normalized.contains(" values "))
        || (normalized.starts_with("create table ")
            && normalized.contains('(')
            && normalized.contains(')'))
}

fn normalize_command(command: &str) -> &str {
    command.trim().trim_end_matches(';').trim()
}

fn is_meta_command(command: &str) -> bool {
    let lower = command.to_ascii_lowercase();
    matches!(lower.as_str(), ".help" | "help" | ".quit" | "quit" | "exit")
}

fn process_command<W>(
    catalog: &mut Catalog,
    command: &str,
    writer: &mut W,
) -> io::Result<CommandFlow>
where
    W: Write,
{
    let normalized = normalize_command(command);
    let lower = normalized.to_ascii_lowercase();

    match lower.as_str() {
        ".help" | "help" => {
            print_repl_help(writer)?;
            Ok(CommandFlow::Continue)
        }
        ".quit" | "quit" | "exit" => {
            writeln!(writer, "bye")?;
            Ok(CommandFlow::Quit)
        }
        _ if is_show_tables_command(normalized) => {
            print_tables(catalog, writer)?;
            Ok(CommandFlow::Continue)
        }
        _ if let Some(schema_command) = parse_schema_command(normalized) => {
            print_schema_command(catalog, schema_command, writer)?;
            Ok(CommandFlow::Continue)
        }
        _ => {
            match execute_sql(catalog, command) {
                Ok(result) => print_execute_result(result, writer)?,
                Err(error) => writeln!(writer, "error: {}", format_execute_error(&error))?,
            }
            Ok(CommandFlow::Continue)
        }
    }
}

fn is_show_tables_command(command: &str) -> bool {
    let lower = command.to_ascii_lowercase();
    matches!(lower.as_str(), "show tables" | "show table")
}

fn parse_schema_command(command: &str) -> Option<SchemaCommand<'_>> {
    let parts = command.split_whitespace().collect::<Vec<_>>();
    let first = parts.first()?;

    if first.eq_ignore_ascii_case(".schema") || first.eq_ignore_ascii_case("schema") {
        return match parts.len() {
            1 => Some(SchemaCommand::All),
            2 => Some(SchemaCommand::Table(parts[1])),
            _ => Some(SchemaCommand::InvalidUsage),
        };
    }

    if first.eq_ignore_ascii_case("describe") {
        return match parts.len() {
            2 => Some(SchemaCommand::Table(parts[1])),
            _ => Some(SchemaCommand::InvalidUsage),
        };
    }

    None
}

fn print_repl_help<W>(writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    writeln!(writer, "commands:")?;
    writeln!(writer, "  CREATE TABLE ...")?;
    writeln!(writer, "  INSERT INTO ... VALUES ...")?;
    writeln!(writer, "  SELECT ... FROM ... [LIMIT n]")?;
    writeln!(writer, "  SHOW TABLES")?;
    writeln!(writer, "  .schema [table]")?;
    writeln!(writer, "  describe <table>")?;
    writeln!(writer, "  .help")?;
    writeln!(writer, "  .quit")?;
    Ok(())
}

fn print_tables<W>(catalog: &Catalog, writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let names = catalog.table_names().collect::<Vec<_>>();

    if names.is_empty() {
        writeln!(writer, "no tables")?;
        return Ok(());
    }

    writeln!(writer, "tables")?;
    writeln!(writer, "------")?;
    for name in &names {
        writeln!(writer, "{name}")?;
    }
    writeln!(
        writer,
        "({} {})",
        names.len(),
        pluralize(names.len(), "table")
    )?;
    Ok(())
}

fn print_schema_command<W>(
    catalog: &Catalog,
    command: SchemaCommand<'_>,
    writer: &mut W,
) -> io::Result<()>
where
    W: Write,
{
    match command {
        SchemaCommand::All => print_all_schemas(catalog, writer),
        SchemaCommand::Table(table_name) => print_table_schema(catalog, table_name, writer),
        SchemaCommand::InvalidUsage => writeln!(writer, "error: usage: .schema [table]"),
    }
}

fn print_all_schemas<W>(catalog: &Catalog, writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let names = catalog.table_names().collect::<Vec<_>>();

    if names.is_empty() {
        writeln!(writer, "no tables")?;
        return Ok(());
    }

    for (index, name) in names.iter().enumerate() {
        if index > 0 {
            writeln!(writer)?;
        }
        print_table_schema(catalog, name, writer)?;
    }

    Ok(())
}

fn print_table_schema<W>(catalog: &Catalog, table_name: &str, writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let table = match catalog.table(table_name) {
        Ok(table) => table,
        Err(error) => {
            writeln!(writer, "error: Catalog({error:?})")?;
            return Ok(());
        }
    };
    let headers = ["#", "column", "type"];
    let rows = table
        .schema()
        .columns()
        .iter()
        .enumerate()
        .map(|(index, column)| {
            vec![
                (index + 1).to_string(),
                column.name().to_string(),
                format!("{:?}", column.value_type()),
            ]
        })
        .collect::<Vec<_>>();
    let widths = column_widths(&headers, &rows);

    writeln!(writer, "table: {}", table.name())?;
    print_cells(&headers, &widths, writer)?;
    print_separator(&widths, writer)?;
    for row in &rows {
        print_cells(row, &widths, writer)?;
    }
    writeln!(
        writer,
        "({} {})",
        rows.len(),
        pluralize(rows.len(), "column")
    )?;
    Ok(())
}

fn print_execute_result<W>(result: ExecuteResult, writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    match result {
        ExecuteResult::CreateTable { table } => writeln!(writer, "created table {table}"),
        ExecuteResult::Insert {
            table,
            rows_inserted,
        } => writeln!(
            writer,
            "inserted {rows_inserted} {} into {table}",
            pluralize(rows_inserted, "row")
        ),
        ExecuteResult::Select { columns, rows } => print_select_result(&columns, &rows, writer),
    }
}

fn print_select_result<W>(columns: &[Column], rows: &[Row], writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    let headers = columns
        .iter()
        .map(|column| column.name())
        .collect::<Vec<_>>();
    let rendered_rows = rows
        .iter()
        .map(|row| row.values().iter().map(format_value).collect::<Vec<_>>())
        .collect::<Vec<_>>();
    let widths = column_widths(&headers, &rendered_rows);

    print_cells(&headers, &widths, writer)?;
    print_separator(&widths, writer)?;
    for row in &rendered_rows {
        print_cells(row, &widths, writer)?;
    }
    writeln!(writer, "({} {})", rows.len(), pluralize(rows.len(), "row"))?;
    Ok(())
}

fn column_widths(headers: &[&str], rows: &[Vec<String>]) -> Vec<usize> {
    let mut widths = headers
        .iter()
        .map(|header| header.len())
        .collect::<Vec<_>>();

    for row in rows {
        for (index, value) in row.iter().enumerate() {
            widths[index] = widths[index].max(value.len());
        }
    }

    widths
}

fn print_cells<W, S>(cells: &[S], widths: &[usize], writer: &mut W) -> io::Result<()>
where
    W: Write,
    S: AsRef<str>,
{
    for (index, cell) in cells.iter().enumerate() {
        if index > 0 {
            write!(writer, " | ")?;
        }
        write!(writer, "{:<width$}", cell.as_ref(), width = widths[index])?;
    }
    writeln!(writer)?;
    Ok(())
}

fn print_separator<W>(widths: &[usize], writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    for (index, width) in widths.iter().enumerate() {
        if index > 0 {
            write!(writer, "-+-")?;
        }
        write!(writer, "{}", "-".repeat(*width))?;
    }
    writeln!(writer)?;
    Ok(())
}

fn format_value(value: &Value) -> String {
    match value {
        Value::Null => String::from("null"),
        Value::Integer(value) => value.to_string(),
        Value::Real(value) => value.to_string(),
        Value::Text(value) => value.clone(),
        Value::Blob(value) => format!("<blob {} bytes>", value.len()),
        Value::Vector(value) => {
            let values = value.iter().map(f32::to_string).collect::<Vec<_>>();
            format!("[{}]", values.join(", "))
        }
    }
}

fn format_execute_error(error: &ExecuteError) -> String {
    format!("{error:?}")
}

fn pluralize(count: usize, singular: &str) -> String {
    if count == 1 {
        singular.to_string()
    } else {
        format!("{singular}s")
    }
}

#[cfg(test)]
mod tests {
    use std::io::Cursor;

    use super::*;

    fn run(input: &str) -> String {
        let mut output = Vec::new();
        run_repl(Cursor::new(input), &mut output).expect("repl should run");
        String::from_utf8(output).expect("output should be utf-8")
    }

    #[test]
    fn repl_executes_create_insert_select_and_show_tables() {
        let output = run("\
create table users (id integer, name text);
insert into users values (1, 'Ada');
select * from users;
show tables;
.quit
");

        assert!(output.contains("created table users"));
        assert!(output.contains("inserted 1 row into users"));
        assert!(output.contains("id | name"));
        assert!(output.contains("1  | Ada"));
        assert!(output.contains("tables"));
        assert!(output.contains("users"));
        assert!(output.contains("bye"));
    }

    #[test]
    fn repl_supports_projection_and_limit_output() {
        let output = run("\
create table users (id integer, name text);
insert into users values (1, 'Ada');
insert into users values (2, 'Grace');
select name from users limit 1;
.quit
");

        assert!(output.contains("name"));
        assert!(output.contains("Ada"));
        assert!(!output.contains("Grace"));
        assert!(output.contains("(1 row)"));
    }

    #[test]
    fn repl_reports_errors_and_continues() {
        let output = run("\
select * from missing;
create table users (id integer);
show table;
.quit
");

        assert!(output.contains("error: Catalog(TableNotFound"));
        assert!(output.contains("created table users"));
        assert!(output.contains("users"));
        assert!(output.contains("bye"));
    }

    #[test]
    fn repl_supports_help_and_empty_show_tables() {
        let output = run("\
.help
show tables;
.quit
");

        assert!(output.contains("commands:"));
        assert!(output.contains("SHOW TABLES"));
        assert!(output.contains(".schema [table]"));
        assert!(output.contains("no tables"));
    }

    #[test]
    fn repl_prints_all_schemas() {
        let output = run("\
create table users (id integer, name text);
create table documents (doc_id integer, embedding vector);
.schema
.quit
");

        assert!(output.contains("table: users"));
        assert!(output.contains("1 | id"));
        assert!(output.contains("2 | name"));
        assert!(output.contains("Integer"));
        assert!(output.contains("Text"));
        assert!(output.contains("table: documents"));
        assert!(output.contains("1 | doc_id"));
        assert!(output.contains("2 | embedding"));
        assert!(output.contains("Vector"));
        assert!(output.contains("(2 columns)"));
    }

    #[test]
    fn repl_prints_single_table_schema_with_describe_alias() {
        let output = run("\
create table users (id integer, name text);
describe users;
.quit
");

        assert!(output.contains("table: users"));
        assert!(output.contains("# | column | type"));
        assert!(output.contains("1 | id     | Integer"));
        assert!(output.contains("2 | name   | Text"));
        assert!(output.contains("(2 columns)"));
    }

    #[test]
    fn repl_supports_schema_without_dot() {
        let output = run("\
create table users (id integer);
schema users;
.quit
");

        assert!(output.contains("table: users"));
        assert!(output.contains("id     | Integer"));
    }

    #[test]
    fn repl_reports_missing_schema_table_and_continues() {
        let output = run("\
.schema missing
create table users (id integer);
show tables;
.quit
");

        assert!(output.contains("error: Catalog(TableNotFound"));
        assert!(output.contains("created table users"));
        assert!(output.contains("tables"));
        assert!(output.contains("users"));
    }
}
