# Music Catalog Bootstrap

[English](README.md)

> MusicBrainz `release` 덤프를 음악 서비스 초기 카탈로그로 변환하는 Python CLI입니다.

`Music Catalog Bootstrap`은 공식 MusicBrainz 덤프나 정규화된 CSV 입력을 읽고, `artist`와 `release` 중심의 기준 카탈로그를 만들며, 각 행을 `AUTO_CREATE`, `AUTO_MATCH`, `REVIEW`, `FAILURE`로 분류한 뒤 dry-run, SQL 생성, 직접 반영 중 하나를 수행합니다.

범위는 초기 카탈로그 bootstrap에 한정됩니다. 복제 파이프라인이나 범용 ETL 도구는 아닙니다.

## 기능

- MusicBrainz `release.tar.xz`, `release.xz`, `release.json`, `release.jsonl` 입력 지원
- 정규화된 CSV 스냅샷 입력 지원
- `artist`, `release` 기준의 기준 카탈로그 누적 저장
- 실행별 `AUTO_CREATE`, `AUTO_MATCH`, `REVIEW`, `FAILURE` 결정 기록
- 실행별 `review_queue.csv` 생성
- `bootstrap` 명령 하나로 dry-run, SQL 생성, 직접 반영 지원
- dry-run 미리보기는 실제 기준 카탈로그 반영과 분리
- 내장 Python 드라이버 기반 MySQL 또는 PostgreSQL 스키마 반영 지원

아키텍처 개요: [ARCHITECTURE.md](ARCHITECTURE.md)
결정 모델: [docs/decision-model.md](docs/decision-model.md)
리뷰 대기열 안내: [docs/review-queue.md](docs/review-queue.md)
직접 반영 안내: [docs/direct-apply.md](docs/direct-apply.md)

## 30초 데모

Windows:

```bat
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data --export-sql out\catalog.sql
```

macOS/Linux:

```sh
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data --export-sql out/catalog.sql
```

`bootstrap` 요약 예시:

```text
Bootstrap summary

Mode:                   dry-run
Run ID:                 run_20260412_085134
Run directory:          .catalog-data/previews/run_20260412_085134

Decision summary
Input rows:             5
AUTO_CREATE:            3
AUTO_MATCH:             0
REVIEW:                 1
FAILURE:                1

Catalog state
Canonical artists:      3
Canonical releases:     3

Target
Engine:                 mysql
Artist table:           service_artists
Release table:          service_releases

Artifacts
Review queue rows:      2
Review queue:           .catalog-data/previews/run_20260412_085134/review_queue.csv
Review summary:         .catalog-data/previews/run_20260412_085134/review-summary.txt

Result
No changes have been applied.
Canonical catalog updated: no
Dry-run did not change the canonical catalog.
Run again with --export-sql or --apply when ready.
Review the flagged rows in .catalog-data/previews/run_20260412_085134/review_queue.csv.
```

## 예제 입력

정규화된 CSV는 다음 컬럼을 기대합니다.

```text
source_id,artist_name,release_title,release_date,upc
```

샘플 일부:

```csv
source_id,artist_name,release_title,release_date,upc
demo-001,Bjork,Debut,1993-07-05,5016958997028
demo-002,Radiohead,OK Computer,1997-05-21,724382885229
demo-003,Radiohead,OK Computer,1997-06-16,
demo-004,My Bloody Valentine,Loveless,1991-11-04,
demo-005,,Unknown Album,1991-11-04,
```

## 예제 결정 로그

```csv
source_id,decision_type,reason_code,canonical_release_id
demo-001,AUTO_CREATE,NEW_RELEASE,1
demo-002,AUTO_CREATE,NEW_RELEASE,2
demo-003,REVIEW,SAME_ARTIST_TITLE_DIFFERENT_DATE,
demo-004,AUTO_CREATE,NEW_RELEASE,3
demo-005,FAILURE,MISSING_REQUIRED_FIELD,
```

## 예제 SQL 출력

```sql
INSERT IGNORE INTO `service_artists` (`name`, `name_key`) VALUES ('Bjork', 'bjork');
INSERT IGNORE INTO `service_artists` (`name`, `name_key`) VALUES ('Radiohead', 'radiohead');

INSERT IGNORE INTO `service_releases` (`artist_id`, `title`, `title_key`, `released_on`, `upc`)
SELECT `id`, 'OK Computer', 'ok computer', '1997-05-21', '724382885229'
FROM `service_artists`
WHERE `name_key` = 'radiohead';
```

추적된 예제 출력:

- [`examples/sample-output/bootstrap-dry-run.txt`](examples/sample-output/bootstrap-dry-run.txt)
- [`examples/sample-output/bootstrap-export-sql.txt`](examples/sample-output/bootstrap-export-sql.txt)
- [`examples/sample-output/bootstrap-apply-postgres.txt`](examples/sample-output/bootstrap-apply-postgres.txt)
- [`examples/sample-output/bootstrap-apply-mysql.txt`](examples/sample-output/bootstrap-apply-mysql.txt)
- [`examples/sample-output/decisions.csv`](examples/sample-output/decisions.csv)
- [`examples/sample-output/review_queue.csv`](examples/sample-output/review_queue.csv)
- [`examples/sample-output/review-summary.txt`](examples/sample-output/review-summary.txt)
- [`examples/sample-output/catalog.sql`](examples/sample-output/catalog.sql)
- [`examples/sample-output/catalog.postgres.sql`](examples/sample-output/catalog.postgres.sql)

직접 반영 예제:

- [`examples/direct-apply/README.md`](examples/direct-apply/README.md)
- [`examples/direct-apply/postgresql/docker-compose.yml`](examples/direct-apply/postgresql/docker-compose.yml)
- [`examples/direct-apply/mysql/docker-compose.yml`](examples/direct-apply/mysql/docker-compose.yml)

## 설치

필수 조건:

- Python 3.10 이상

옵션 1. GitHub Release ZIP 사용

- release ZIP을 다운로드해 압축을 풉니다
- Windows: `bin\music-catalog-bootstrap.bat`
- macOS/Linux: `sh ./bin/music-catalog-bootstrap`
- `dry-run`, `export-sql`은 추가 설치 없이 실행할 수 있습니다
- `--apply`를 쓰려면 같은 Python 환경에 선택 의존성을 설치해야 합니다:

```sh
python -m pip install ".[apply]"
```

옵션 2. 설치 없이 소스에서 바로 실행

- Windows: `catalog.bat`
- macOS/Linux: `sh ./catalog`

옵션 3. 소스 설치

```sh
python -m pip install -e .
music-catalog-bootstrap --help
```

직접 반영까지 쓰려면:

```sh
python -m pip install -e ".[apply]"
```

## 빠른 시작

저장소에 포함된 샘플 파일:

- MusicBrainz 샘플 입력: `fixtures/musicbrainz_release_subset.jsonl`
- CSV 샘플 입력: `fixtures/sample_releases.csv`
- MySQL 대상 프로필: `fixtures/sample-target.properties`
- PostgreSQL 대상 프로필: `fixtures/sample-target-postgres.properties`
- PostgreSQL 직접 반영 예제 프로필: `fixtures/sample-target-postgres-apply.properties`
- MySQL 직접 반영 예제 프로필: `fixtures/sample-target-mysql-apply.properties`

실제 입력 데이터는 다음에서 받을 수 있습니다.

- `https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/`
- 최신 날짜 디렉터리에서 `release.tar.xz` 다운로드
- 이 도구는 `release.tar.xz`를 그대로 읽을 수 있음

정규화된 CSV로 실행:

Windows:

```bat
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data --export-sql out\catalog.sql
```

macOS/Linux:

```sh
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data --export-sql out/catalog.sql
```

MusicBrainz 덤프로 실행:

Windows:

```bat
catalog.bat bootstrap downloads\release.tar.xz fixtures\sample-target.properties --input-kind musicbrainz --data-dir .catalog-data
```

macOS/Linux:

```sh
sh ./catalog bootstrap downloads/release.tar.xz fixtures/sample-target.properties --input-kind musicbrainz --data-dir .catalog-data
```

직접 반영용 설정이 들어 있는 대상 프로필이라면:

```bat
catalog.bat bootstrap downloads\release.tar.xz fixtures\sample-target-postgres-apply.properties --input-kind musicbrainz --data-dir .catalog-data --apply
```

로컬 도커 기반 직접 반영 스모크 테스트:

Windows:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\scripts\smoke-apply.ps1 -Engine postgresql -Cleanup
PowerShell -ExecutionPolicy Bypass -File .\scripts\smoke-apply.ps1 -Engine mysql -Cleanup
```

macOS/Linux:

```sh
sh ./scripts/smoke-apply -Engine postgresql -Cleanup
sh ./scripts/smoke-apply -Engine mysql -Cleanup
```

## 명령어

| 명령어 | 설명 |
| --- | --- |
| `bootstrap <input-path> <target-profile> [--data-dir DIR] [--input-kind auto\|csv\|musicbrainz] [--export-sql FILE] [--apply]` | 입력을 가져오고 기준 카탈로그를 만든 뒤 `review_queue.csv`를 생성하고 dry-run, SQL 생성, 직접 반영 중 하나를 수행합니다. |
| `import-musicbrainz <release-file\|release.xz\|release.tar.xz\|directory> [data-dir]` | MusicBrainz `release` 덤프 또는 해당 파일이 들어 있는 디렉터리를 가져옵니다. |
| `import <csv-file> [data-dir]` | 정규화된 CSV 스냅샷을 가져옵니다. |
| `plan <target-profile> [data-dir]` | 대상 프로필을 검증하고 현재 카탈로그 및 최신 실행 요약을 출력합니다. |
| `export-sql <target-profile> <output-file> [data-dir]` | 현재 카탈로그를 기준으로 SQL 파일을 생성합니다. |

기본 `data-dir`은 `.catalog-data`입니다.

## 대상 프로필

예제 대상 프로필은 `fixtures/sample-target.properties`, `fixtures/sample-target-postgres.properties`, `fixtures/sample-target-postgres-apply.properties`, `fixtures/sample-target-mysql-apply.properties`에 있습니다.

```properties
target.engine=mysql
target.write_mode=insert-ignore

artist.table=service_artists
artist.id.column=id
artist.lookup.column=name_key
artist.name.column=name
artist.name_key.column=name_key

release.table=service_releases
release.artist_id.column=artist_id
release.title.column=title
release.title_key.column=title_key
release.date.column=released_on
release.upc.column=upc
```

```properties
target.engine=postgresql
target.write_mode=insert-ignore
```

직접 반영에 쓰는 선택 설정:

```properties
target.apply.mode=driver
target.apply.host=localhost
target.apply.port=55432
target.apply.database=music_app
target.apply.user=bootstrap
target.apply.password_env=MCB_PG_PASSWORD
```

로컬 클라이언트 명령을 강제로 쓰고 싶다면:

```properties
target.apply.mode=command
target.apply.command=psql
```

## 테스트

```sh
python -m unittest discover -s tests -v
```

## 릴리스 ZIP 빌드

- Windows: `scripts\build-release.bat`
- PowerShell: `.\scripts\build-release.ps1`
- 공통: `python scripts/build-release.py`

생성된 ZIP은 `build/distributions/` 아래에 위치합니다.

## 현재 범위와 한계

- 대상 엔진: `mysql`, `postgresql`
- 쓰기 방식: `insert-ignore`
- 엔티티 범위: `artist`, `release`
- 직접 반영은 기본적으로 내장 Python 드라이버를 사용하고, 필요하면 로컬 클라이언트 명령으로도 실행할 수 있습니다
- PostgreSQL과 MySQL 직접 반영 스모크 검증은 CI에서도 실행합니다
- 미지원: 증분 동기화, `track`/`recording` 중심 적재, MySQL/PostgreSQL 외 다른 엔진

## 로드맵

- release automation
- 더 쉬운 설치 경로
- 추가 출력 대상
- 더 넓은 엔티티 범위

## 라이선스

이 저장소는 [MIT License](LICENSE)를 따릅니다.

추가 문서: [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md)
