use std::io::{self, BufRead, Write};

use crate::{execute_sql, Catalog, Column, ExecuteError, ExecuteResult, Row, Value};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CommandFlow {
    Continue,
    Quit,
}

pub fn run_repl<R, W>(mut reader: R, writer: &mut W) -> io::Result<()>
where
    R: BufRead,
    W: Write,
{
    let mut catalog = Catalog::new();
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
                process_command(&mut catalog, pending.trim(), writer)?;
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

        let flow = process_command(&mut catalog, pending.trim(), writer)?;
        pending.clear();

        if flow == CommandFlow::Quit {
            break;
        }
    }

    Ok(())
}

fn is_complete_command(command: &str) -> bool {
    let trimmed = command.trim();
    let normalized = normalize_command(trimmed);

    is_meta_command(normalized)
        || is_show_tables_command(normalized)
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

fn print_repl_help<W>(writer: &mut W) -> io::Result<()>
where
    W: Write,
{
    writeln!(writer, "commands:")?;
    writeln!(writer, "  CREATE TABLE ...")?;
    writeln!(writer, "  INSERT INTO ... VALUES ...")?;
    writeln!(writer, "  SELECT ... FROM ... [LIMIT n]")?;
    writeln!(writer, "  SHOW TABLES")?;
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
        assert!(output.contains("no tables"));
    }
}
