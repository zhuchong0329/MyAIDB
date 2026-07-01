#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
seed_dir="$(mktemp -d "${TMPDIR:-/tmp}/myaidb-seed.XXXXXX")"
seed_file="${seed_dir}/seed.sql"

cleanup() {
  rm -rf "${seed_dir}"
}
trap cleanup EXIT

cat >"${seed_file}" <<'SQL'
-- MyAIDB development seed data.
-- 5 tables, 12 rows each.

create table users (id integer, name text, age integer);
insert into users values (1, 'Ada', 37);
insert into users values (2, 'Grace', 17);
insert into users values (3, 'Linus', 18);
insert into users values (4, 'Barbara', 45);
insert into users values (5, 'Donald', 29);
insert into users values (6, 'Edsger', 41);
insert into users values (7, 'Frances', 33);
insert into users values (8, 'Ken', 52);
insert into users values (9, 'Margaret', 36);
insert into users values (10, 'Niklaus', 31);
insert into users values (11, 'Radia', 48);
insert into users values (12, 'Tim', 26);

create table products (id integer, name text, price real);
insert into products values (1, 'keyboard', 99.5);
insert into products values (2, 'mouse', 39.0);
insert into products values (3, 'monitor', 249.99);
insert into products values (4, 'laptop', 1299.0);
insert into products values (5, 'dock', 189.5);
insert into products values (6, 'webcam', 79.99);
insert into products values (7, 'microphone', 119.0);
insert into products values (8, 'chair', 349.0);
insert into products values (9, 'desk', 499.0);
insert into products values (10, 'tablet', 699.0);
insert into products values (11, 'phone', 899.0);
insert into products values (12, 'headphones', 159.0);

create table orders (id integer, user_id integer, product_id integer, quantity integer);
insert into orders values (1, 1, 4, 1);
insert into orders values (2, 2, 2, 2);
insert into orders values (3, 3, 1, 1);
insert into orders values (4, 4, 3, 2);
insert into orders values (5, 5, 8, 1);
insert into orders values (6, 6, 7, 3);
insert into orders values (7, 7, 5, 1);
insert into orders values (8, 8, 9, 1);
insert into orders values (9, 9, 6, 2);
insert into orders values (10, 10, 10, 1);
insert into orders values (11, 11, 12, 2);
insert into orders values (12, 12, 11, 1);

create table documents (id integer, title text, score real);
insert into documents values (1, 'intro to databases', 0.91);
insert into documents values (2, 'query planner notes', 0.83);
insert into documents values (3, 'rust ownership guide', 0.95);
insert into documents values (4, 'storage engine sketch', 0.74);
insert into documents values (5, 'cli user manual', 0.88);
insert into documents values (6, 'parser design memo', 0.8);
insert into documents values (7, 'executor pipeline', 0.93);
insert into documents values (8, 'index roadmap', 0.7);
insert into documents values (9, 'transaction ideas', 0.69);
insert into documents values (10, 'testing strategy', 0.86);
insert into documents values (11, 'schema evolution', 0.76);
insert into documents values (12, 'vector search plan', 0.82);

create table events (id integer, user_id integer, event_type text, created_at integer);
insert into events values (1, 1, 'login', 1001);
insert into events values (2, 1, 'query', 1002);
insert into events values (3, 2, 'login', 1003);
insert into events values (4, 3, 'insert', 1004);
insert into events values (5, 4, 'query', 1005);
insert into events values (6, 5, 'logout', 1006);
insert into events values (7, 6, 'login', 1007);
insert into events values (8, 7, 'query', 1008);
insert into events values (9, 8, 'insert', 1009);
insert into events values (10, 9, 'query', 1010);
insert into events values (11, 10, 'login', 1011);
insert into events values (12, 11, 'logout', 1012);
SQL

echo "Starting MyAIDB with development seed data..."
echo "Seed file: ${seed_file}"
echo
echo "Try:"
echo "  show tables;"
echo "  .schema users;"
echo "  select name, age from users where age >= 30 order by age desc limit 5;"
echo "  select title, score from documents where score >= 0.85 order by score desc;"
echo

cargo run --manifest-path "${repo_root}/Cargo.toml" -- --seed "${seed_file}"
