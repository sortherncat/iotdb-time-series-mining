# Development Log

## 2026-09-01 - Task 1.1 Apache IoTDB Deployment

### Objective

Deploy Apache IoTDB in standalone mode and verify that the service can be accessed through the IoTDB CLI.

### Environment

- Operating system: macOS
- IoTDB version: Apache IoTDB 2.0.4
- Java version: OpenJDK 8
- Default IoTDB RPC address: `127.0.0.1`
- Default IoTDB RPC port: `6667`
- Default user: `root`
- Default password: `root`

### Step 1: Check Java

IoTDB depends on Java, so check the local Java environment first.

```bash
java -version
```

If Java is installed correctly, the terminal should print a version number, for example:

```text
openjdk version "1.8..."
```

### Step 2: Download Apache IoTDB

Download the Apache IoTDB 2.0.4 binary package.

```bash
cd ~/Downloads
curl -L -o apache-iotdb-2.0.4-all-bin.zip https://archive.apache.org/dist/iotdb/2.0.4/apache-iotdb-2.0.4-all-bin.zip
```

### Step 3: Extract the Package

```bash
unzip apache-iotdb-2.0.4-all-bin.zip
cd apache-iotdb-2.0.4-all-bin
```

### Step 4: Fix DataNode JVM Stack Size on macOS

On this machine, DataNode may fail to start with the following error:

```text
The stack size specified is too small, Specify at least 640k
```

To avoid this issue, edit the DataNode JVM configuration file:

```bash
nano conf/datanode-env.sh
```

Find:

```bash
-Xss512k
```

Change it to:

```bash
-Xss1m
```

Save the file and exit.

### Step 5: Start IoTDB Standalone Mode

Run the startup script from the IoTDB root directory:

```bash
./sbin/start-standalone.sh
```

Expected output:

```text
Execute start-standalone.sh finished, you can see more details in the logs of confignode and datanode
```

### Step 6: Verify with CLI

Use the IoTDB CLI to connect to the local IoTDB service.

```bash
./sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root
```

After entering the CLI, run:

```sql
show databases;
```

It is also possible to verify with one command:

```bash
./sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root -e "show databases"
```

For a new IoTDB instance, the expected result is:

```text
Empty set.
```

This means the IoTDB service is running correctly, but no database has been created yet.

### Step 7: Stop IoTDB

After verification, stop IoTDB if it is not needed temporarily.

```bash
./sbin/stop-standalone.sh
```

### Verification Result

The CLI verification command was executed successfully:

```sql
show databases;
```

The result was:

```text
Empty set.
It costs 0.072s
```

Therefore, Apache IoTDB 2.0.4 standalone deployment and CLI verification were completed successfully.

### Notes

- If `start-standalone.sh` reports success but the CLI cannot connect, check whether port `6667` is listening.
- If DataNode fails because of stack size, update `conf/datanode-env.sh` from `-Xss512k` to `-Xss1m`.
- The default IoTDB connection information is `127.0.0.1:6667`, user `root`, password `root`.

## 2026-09-01 - Task 1.2 ETTh1 Data Import Design

### Objective

Import the selected multivariate time series dataset ETTh1 into Apache IoTDB with a self-written Python script and batched Session API writes.

### Selected Dataset

- Dataset: ETTh1
- Source project: ETT Dataset
- File name: `ETTh1.csv`
- Format: CSV
- Time column: `date`
- Sensor columns: `HUFL`, `HULL`, `MUFL`, `MULL`, `LUFL`, `LULL`, `OT`

### Local Data Path

The raw dataset should be placed at:

```text
data/raw/ETTh1.csv
```

The `data/raw/` directory is ignored by Git because datasets should not be committed to the repository.

### Download Command

```bash
mkdir -p data/raw
curl -L -o data/raw/ETTh1.csv https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
```

If GitHub raw download is slow or blocked, download `ETTh1.csv` manually from:

```text
https://github.com/zhouhaoyi/ETDataset/tree/main/ETT-small
```

Then place it under `data/raw/ETTh1.csv`.

### IoTDB Storage Path Design

ETTh1 describes transformer load and oil temperature data, so the device path is designed as:

```text
root.industry.transformer001
```

The measurement paths are:

```text
root.industry.transformer001.high_useful_load
root.industry.transformer001.high_useless_load
root.industry.transformer001.middle_useful_load
root.industry.transformer001.middle_useless_load
root.industry.transformer001.low_useful_load
root.industry.transformer001.low_useless_load
root.industry.transformer001.oil_temperature
```

This path design follows IoTDB's hierarchical structure:

```text
root -> industry -> transformer001 -> measurement
```

### Import Script

The import implementation is located in:

```text
data_loader.py
```

The script does the following:

- Reads `ETTh1.csv` with pandas.
- Checks required columns.
- Converts `date` values into millisecond timestamps.
- Creates the IoTDB database `root.industry`.
- Writes all seven sensor columns under `root.industry.transformer001`.
- Uses batched `insert_records` calls, with a default batch size of 1000 rows.

### Import Command

Start IoTDB first, then run:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

Expected progress output:

```text
Imported 1000/17420 rows
Imported 2000/17420 rows
...
Finished importing 17420 rows to root.industry.transformer001
```

### Notes

- IoTDB must be running before executing `data_loader.py`.
- The default connection is `127.0.0.1:6667`, user `root`, password `root`.
- All ETTh1 sensor values are imported as `DOUBLE`.
- The current implementation focuses on task 1.2 data import; full range query helpers will be completed in task 1.3.

### Import Verification

The import script was executed successfully:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

Result:

```text
Finished importing 17420 rows to root.industry.transformer001
```

The database was verified with:

```sql
show databases;
```

Result:

```text
root.industry
```

The time series were verified with:

```sql
show timeseries root.industry.**;
```

Result:

```text
root.industry.transformer001.high_useful_load
root.industry.transformer001.high_useless_load
root.industry.transformer001.middle_useful_load
root.industry.transformer001.middle_useless_load
root.industry.transformer001.low_useful_load
root.industry.transformer001.low_useless_load
root.industry.transformer001.oil_temperature
```

The first rows were verified with:

```sql
select * from root.industry.transformer001 limit 5;
```

The query returned five rows starting from:

```text
2016-07-01T08:00:00.000+08:00
```

Therefore, task 1.2 data import and batch-write verification were completed successfully.

## 2026-09-01 - IoTDB Reproducible Setup Scripts

### Objective

Avoid committing the full Apache IoTDB binary package to Git while still allowing another user to reproduce the same local environment after cloning the repository.

### Design Decision

The IoTDB binary package is not stored in the repository because it is large and contains runtime directories such as data and logs. Instead, the project provides shell scripts under `scripts/`.

### Added Scripts

```text
scripts/setup_iotdb.sh
scripts/start_iotdb.sh
scripts/check_iotdb.sh
scripts/stop_iotdb.sh
```

### Script Functions

- `setup_iotdb.sh`: downloads Apache IoTDB 2.0.4 into `third_party/`, extracts it, and applies the DataNode stack-size fix.
- `start_iotdb.sh`: starts IoTDB in standalone mode.
- `check_iotdb.sh`: uses IoTDB CLI to execute `show databases`.
- `stop_iotdb.sh`: stops IoTDB standalone mode.

### Git Ignore Rule

The following local runtime files are ignored:

```text
third_party/apache-iotdb-*/
third_party/*.zip
```

Only `third_party/.gitkeep` is committed, so the folder structure exists after cloning.

### Reproduction Steps for a New User

```bash
bash scripts/setup_iotdb.sh
bash scripts/start_iotdb.sh
bash scripts/check_iotdb.sh
```

Expected verification result:

```text
Empty set.
```

This means IoTDB is running correctly and can be accessed through the CLI.

## 2026-09-01 - Improve IoTDB Startup Waiting Logic

### Problem

When the following commands were executed continuously:

```bash
bash scripts/setup_iotdb.sh
bash scripts/start_iotdb.sh
bash scripts/check_iotdb.sh
```

the `check_iotdb.sh` script sometimes failed with:

```text
ErrorCan't execute sql becauseConnection Error, please check whether the network is available or the server has started.
```

The reason was that `start-standalone.sh` returns after sending the startup command, but DataNode still needs several seconds to finish initialization and open the RPC service on port `6667`.

### Modification

Updated:

```text
scripts/start_iotdb.sh
```

After running `start-standalone.sh`, the script now waits for IoTDB to become queryable.

The script repeatedly executes:

```bash
./sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root -e "show databases"
```

It checks every 2 seconds and waits up to 60 seconds.

### Result

If IoTDB becomes available, the script prints:

```text
Apache IoTDB is ready.
Verify with: bash scripts/check_iotdb.sh
```

If IoTDB is still unavailable after 60 seconds, it prints the log path:

```text
IoTDB did not become ready within 60 seconds.
Check logs under: third_party/apache-iotdb-2.0.4-all-bin/logs
```

### Additional Check Script Improvement

Updated:

```text
scripts/check_iotdb.sh
```

When the CLI connection fails, the script now prints a clearer message:

```text
Failed to connect to IoTDB at 127.0.0.1:6667.
Please make sure IoTDB is running:
  bash scripts/start_iotdb.sh
```

This makes startup timing problems easier to understand.

## 2026-09-01 - Fix Data Import Module Compatibility

### Problem 1: Session Constructor Argument

When running:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

the first error was:

```text
TypeError: Session.__init__() got an unexpected keyword argument 'ip'
```

The installed `apache-iotdb` Python client uses the following constructor style:

```python
Session(host, port, user, password, fetch_size, zone_id, enable_redirection=True)
```

It does not accept the keyword argument `ip`.

### Modification 1

Updated:

```text
data_loader.py
```

Changed the Session creation from keyword arguments:

```python
Session(
    ip=config.host,
    port=config.port,
    user=config.user,
    password=config.password,
    fetch_size=config.fetch_size,
    zone_id=config.zone_id,
    enable_redirection=True,
)
```

to positional arguments:

```python
Session(
    config.host,
    config.port,
    config.user,
    config.password,
    config.fetch_size,
    config.zone_id,
    enable_redirection=True,
)
```

The default time zone was also changed from:

```text
UTC+8
```

to:

```text
Asia/Shanghai
```

which matches the Python client default and local environment better.

### Problem 2: IoTDB Data Type Argument

After fixing the Session constructor, the next error was:

```text
RuntimeError: Unsupported data type:DOUBLE
```

The current Python IoTDB client does not accept the plain string `"DOUBLE"` for batch insert data types. It expects the `TSDataType` enum.

### Modification 2

Updated:

```text
data_loader.py
```

Imported:

```python
from iotdb.utils.IoTDBConstants import TSDataType
```

Changed data types from:

```python
data_types = ["DOUBLE"] * len(measurements)
```

to:

```python
data_types = [TSDataType.DOUBLE] * len(measurements)
```

### Problem 3: Repeated Database Creation

When the import script is run multiple times, the database `root.industry` may already exist.

### Modification 3

The database creation statement is now wrapped with a simple duplicate-existence guard:

```python
try:
    session.execute_non_query_statement("CREATE DATABASE root.industry")
except Exception as exc:
    message = str(exc).lower()
    if "already" not in message and "exist" not in message:
        raise
```

This allows repeated import attempts without failing only because the database already exists.

### Final Verification

After the modifications, the import command completed successfully:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

Result:

```text
Imported 17420/17420 rows
Finished importing 17420 rows to root.industry.transformer001
```

The imported data was verified through IoTDB CLI:

```sql
show databases;
show timeseries root.industry.**;
select * from root.industry.transformer001 limit 5;
```

The result confirmed that `root.industry` was created, seven ETTh1 measurements were imported, and the first five rows could be queried successfully.

## 2026-09-01 - Task 1.3 Time Range Query and DataFrame Conversion

### Objective

Query multivariate ETTh1 time series data from Apache IoTDB by a specified time range and convert the result into a `pandas.DataFrame` for later segmentation, feature extraction, and clustering.

### Query Method

The query function is implemented in:

```text
data_loader.py
```

The function name is:

```python
query_etth1_from_iotdb(...)
```

It uses the IoTDB Session API to execute SQL:

```sql
SELECT high_useful_load, high_useless_load, middle_useful_load, middle_useless_load,
       low_useful_load, low_useless_load, oil_temperature
FROM root.industry.transformer001
WHERE time >= ${start_ms} AND time <= ${end_ms}
```

The returned `SessionDataSet` is converted to a `pandas.DataFrame` through the IoTDB Python client's `todf()` method.

### Time Conversion

The input time strings are converted to millisecond timestamps with pandas:

```python
int(pd.Timestamp(time_text).value // 1_000_000)
```

This keeps the query timestamp conversion consistent with the timestamp conversion used during data import.

### DataFrame Format

The query result DataFrame contains:

- `Time`: IoTDB millisecond timestamp
- `datetime`: pandas datetime converted from `Time`
- `high_useful_load`
- `high_useless_load`
- `middle_useful_load`
- `middle_useless_load`
- `low_useful_load`
- `low_useless_load`
- `oil_temperature`

The full IoTDB path column names are renamed to short measurement names so that later analysis modules can use them directly.

### Command Line Usage

Query a time range and print a preview:

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00"
```

Query a time range and save the DataFrame as CSV:

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --output data/processed/etth1_query_sample.csv
```

### Compatibility Note

The original import command is still supported:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

Internally, this is treated as the `import` command so that previous usage does not break.

## 2026-09-01 - Task 2 Method A ruptures Change Point Detection

### Objective

Implement the first automatic segmentation method for high-dimensional time series data.

Method A uses the `ruptures` library to detect unknown transition points between operating conditions. The method performs joint detection on the multivariate ETTh1 sensor matrix instead of detecting each dimension independently.

### Implementation File

The implementation is located in:

```text
segmentation.py
```

### Dependency

Added the following dependency to:

```text
requirements.txt
```

```text
ruptures>=1.1.9
```

### Data Preparation

The segmentation module supports two input formats:

- The original ETTh1 CSV with columns `HUFL`, `HULL`, `MUFL`, `MULL`, `LUFL`, `LULL`, `OT`.
- The queried DataFrame CSV from IoTDB with columns such as `high_useful_load` and `oil_temperature`.

Before change point detection, the seven sensor columns are selected and standardized:

```text
standardized_value = (value - column_mean) / column_std
```

This avoids variables with larger numeric ranges dominating the detection result.

### Method A Design

The current Method A uses:

```python
ruptures.Pelt(model="rbf", min_size=48, jump=10)
```

Parameter meaning:

- `model="rbf"`: detects nonlinear distribution changes in multivariate data.
- `min_size=48`: each segment should contain at least 48 hourly records.
- `jump=10`: evaluates candidate change points every 10 records to improve speed on the full ETTh1 dataset.
- `penalty=10`: controls the number of detected change points. A larger penalty usually produces fewer segments.

### Fine-Grained Boundary Refinement

The first version used `jump=10`, so the detected boundaries tended to appear around multiples of 10. To improve boundary precision without making the whole search too slow, the implementation was updated to use a two-stage strategy:

```text
Stage 1: coarse search with ruptures PELT and jump=10
Stage 2: fine local search around each coarse change point with step size 1
```

For each coarse change point `cp`, the refined search checks candidate points in:

```text
[cp - refine_radius, cp + refine_radius]
```

while still respecting the minimum segment length constraint. For each candidate boundary, the algorithm computes:

```text
cost(left segment) + cost(right segment)
```

and keeps the candidate with the lowest total cost.

The related command line parameters are:

- `--refine`: enable fine-grained local boundary refinement.
- `--no-refine`: disable refinement and keep coarse boundaries.
- `--refine-radius 20`: search 20 records before and after each coarse boundary.

### Output Format

The module returns:

```python
SegmentationResult(
    method="ruptures_pelt",
    model="rbf",
    penalty=10,
    min_size=48,
    jump=10,
    refine=True,
    refine_radius=20,
    coarse_change_points=[...],
    change_points=[...],
    segments=[(start_1, end_1), (start_2, end_2), ...],
)
```

The final task output is the `segments` list:

```python
[(start_1, end_1), (start_2, end_2), ...]
```

The boundaries use half-open row index intervals, meaning each segment contains rows:

```text
start <= row_index < end
```

### Command Line Usage

Run Method A on the complete ETTh1 CSV:

```bash
python segmentation.py \
  --input data/raw/ETTh1.csv \
  --model rbf \
  --penalty 10 \
  --min-size 48 \
  --jump 10 \
  --refine \
  --refine-radius 20
```

### Verification Result

The command was executed successfully on the complete ETTh1 dataset.

Result summary:

```text
Detected 38 change points
Generated 39 segments
Saved result to outputs/segmentation/method_a_ruptures.json
```

Example coarse and refined boundaries:

```text
50 -> 48
250 -> 249
540 -> 549
790 -> 791
930 -> 932
```

Example refined segment boundaries:

```python
[(0, 48), (48, 249), (249, 549), (549, 791), (791, 932)]
```

The minimum segment length constraint was also checked:

```text
minimum segment length: 48
maximum segment length: 1415
number of segments: 39
all segments satisfy min_size=True
```

This completes Method A of Task 2. Method B will be implemented separately for comparison.

## 2026-09-01 - Encapsulate Method A as a Reusable Module

### Objective

Refactor the two-stage ruptures segmentation logic into a reusable code module so that later pipeline code can call Method A directly instead of only running it through the command line script.

### New Module

Added:

```text
src/ruptures_segmenter.py
```

This module contains:

- `RupturesSegmenter`: reusable two-stage PELT segmenter.
- `SegmentationResult`: structured result object.
- `prepare_feature_matrix(...)`: multivariate sensor selection and standardization.
- `refine_change_points_near_coarse_boundaries(...)`: local fine-grained boundary search.
- `segments_from_change_points(...)`: change point list to segment interval conversion.

### Command Line Script Update

The top-level script:

```text
segmentation.py
```

now acts mainly as a command line wrapper. It loads the input CSV, creates a `RupturesSegmenter`, runs segmentation, and saves the result JSON.

### Usage from Python Code

Example:

```python
import pandas as pd

from src.ruptures_segmenter import RupturesSegmenter

df = pd.read_csv("data/raw/ETTh1.csv")

segmenter = RupturesSegmenter(
    model="rbf",
    penalty=10,
    min_size=48,
    jump=10,
    refine=True,
    refine_radius=20,
)

result = segmenter.segment(df)
segments = result.segments
```

### Verification Result

After refactoring, the same full ETTh1 command was executed successfully:

```bash
python segmentation.py \
  --input data/raw/ETTh1.csv \
  --model rbf \
  --penalty 10 \
  --min-size 48 \
  --jump 10 \
  --refine \
  --refine-radius 20
```

The result remained consistent:

```text
Detected 38 change points
Generated 39 segments
```

## 2026-09-01 - Task 2 Method B Sliding Window Statistical Distance

### Objective

Implement the second automatic segmentation method for comparison with Method A.

Method B detects change points by comparing the statistical distribution of the left and right windows around each candidate time point.

### Implementation File

Added:

```text
src/window_stat_segmenter.py
```

The command line entry is still:

```text
segmentation.py
```

Use `--method window_stat` to run Method B.

### Mathematical Definition

For each candidate time point `t`, construct:

```text
L_t = X[t - w : t]
R_t = X[t : t + w]
```

The mean distance is:

```text
D_mu(t) = ||mu_L - mu_R||_2
```

The covariance distance is:

```text
D_cov(t) = ||Sigma_L - Sigma_R||_F
```

The final change score is:

```text
S(t) = D_mu(t) + alpha * D_cov(t)
```

The implementation uses standardized multivariate sensor data, so all seven ETTh1 variables contribute on comparable scales.

### Peak Selection

After computing the score curve, candidate change points are selected as local peaks:

```text
S(t) > S(t - 1)
S(t) > S(t + 1)
S(t) >= threshold
```

The threshold is computed by score quantile:

```text
threshold = Q_0.95(S)
```

### Minimum Segment Length Constraint

Candidate peaks are sorted by score from high to low. A candidate is kept only if adding it does not create any segment shorter than `min_size`.

This keeps strong change points while avoiding very short fragments.

### Main Classes and Functions

The module contains:

- `WindowStatSegmenter`: reusable sliding-window statistical-distance segmenter.
- `compute_window_stat_scores(...)`: computes the full `S(t)` score curve.
- `find_local_peak_change_points(...)`: finds local peaks above the threshold.
- `filter_change_points_by_min_size(...)`: applies the minimum segment length constraint.
- `WindowStatSegmentationResult`: structured result object.

### Command Line Usage

Run Method B on the complete ETTh1 CSV:

```bash
python segmentation.py \
  --method window_stat \
  --input data/raw/ETTh1.csv \
  --window-size 48 \
  --alpha 0.5 \
  --threshold-quantile 0.95 \
  --min-size 48
```

### Verification Result

The command was executed successfully on the complete ETTh1 dataset.

Result summary:

```text
Detected 32 change points
Generated 33 segments
Threshold: 3.412608
Saved result to outputs/segmentation/method_b_window_stat.json
```

Example change points:

```python
[809, 2864, 3788, 3836, 6580, 6833, 7303, 8191, 9085, 9319]
```

Example segment boundaries:

```python
[(0, 809), (809, 2864), (2864, 3788), (3788, 3836), (3836, 6580)]
```

The minimum segment length constraint was checked:

```text
minimum segment length: 48
maximum segment length: 2744
number of segments: 33
all segments satisfy min_size=True
```

This completes Method B of Task 2.

## 2026-09-01 - Store Segmentation Results Independently

### Objective

Avoid overwriting segmentation results when Method A and Method B are executed separately.

### Change

Updated:

```text
segmentation.py
```

If `--output` is not specified, each method now writes to its own default output file:

```text
outputs/segmentation/method_a_ruptures.json
outputs/segmentation/method_b_window_stat.json
```

Manual `--output` paths are still supported.

### Verification Result

Both methods were executed without manually specifying `--output`.

Method A:

```text
Saved result to outputs/segmentation/method_a_ruptures.json
```

Method B:

```text
Saved result to outputs/segmentation/method_b_window_stat.json
```

## 2026-09-01 - Compare Method A and Method B Segmentation Results

### Objective

Compare the segmentation results produced by Method A and Method B from a data perspective.

### Result Files

Method A result:

```text
outputs/segmentation/method_a_ruptures.json
```

Method B result:

```text
outputs/segmentation/method_b_window_stat.json
```

### Basic Comparison

Method A:

```text
method: ruptures_pelt
change points: 38
segments: 39
```

Method B:

```text
method: window_stat_distance
change points: 32
segments: 33
```

Method A detects 6 more change points than Method B. This means Method A is more sensitive and produces finer segmentation, while Method B is relatively more conservative.

### Boundary Matching Analysis

If two change points are considered matched when their distance is no larger than 48 records, the matching result is:

```text
A matched by B: 19 / 38 = 50.0%
B matched by A: 17 / 32 = 53.1%
```

If the tolerance is relaxed to 96 records:

```text
A matched by B: 23 / 38 = 60.5%
B matched by A: 23 / 32 = 71.9%
```

This shows that many Method B change points can also be found near Method A boundaries, but Method A contains additional local change points that Method B does not select.

### Nearest-Distance Statistics

For each Method A change point, the nearest Method B change point distance is:

```text
min: 0
median: 47.5
mean: 228.9
75% quantile: 257.0
max: 1147
```

For each Method B change point, the nearest Method A change point distance is:

```text
min: 0
median: 31.5
mean: 77.6
75% quantile: 116.5
max: 368
```

The nearest-distance statistics indicate that Method B boundaries are generally closer to some Method A boundary than the reverse. In other words, Method B behaves more like a subset of stronger changes, while Method A detects more minor transitions.

### Segment Length Comparison

Method A segment length statistics:

```text
min: 48
median: 300.0
mean: 446.7
75% quantile: 728.0
max: 1415
```

Method B segment length statistics:

```text
min: 48
median: 237.0
mean: 527.9
75% quantile: 809.0
max: 2744
```

Method B has a larger average segment length and a much longer maximum segment, which means it leaves some relatively stable periods unsegmented. Method A cuts these periods into more detailed subsegments.

### Consistent Change Points

Several boundaries detected by the two methods are close to each other:

```text
A 791   ~ B 809
A 2856  ~ B 2864
A 3777  ~ B 3788
A 3836  = B 3836
A 6848  ~ B 6833
A 8191  = B 8191
A 9082  ~ B 9085
A 9309  ~ B 9319
A 10866 = B 10866
A 16294 ~ B 16289
```

These consistent boundaries are more reliable because both methods detect significant changes near the same positions.

### Main Difference

Method A detects many early-stage local boundaries:

```text
48, 249, 549, 932, 1212, 1351, 1832, 2616
```

Their corresponding dates are mainly between:

```text
2016-07-03 and 2016-10
```

Method B's first detected boundary is:

```text
809
```

which corresponds to:

```text
2016-08-03 17:00:00
```

This suggests that Method B ignores some small early fluctuations because their sliding-window statistical distance scores are not high enough to pass the quantile threshold.

### Conclusion

The difference between the two methods is moderate to large, but reasonable.

Method A is more sensitive and suitable for capturing finer local distribution changes. Method B is more conservative and focuses on changes where the left and right window statistics differ more strongly.

For the report, the comparison can be summarized as:

```text
Method A detects more local transition points, while Method B detects fewer but stronger statistical distribution changes. The two methods agree around several major boundaries, such as 3836, 8191, 10866, and 16290, suggesting that these positions are likely to be significant operating-condition transition points.
```

## 2026-09-01 - Task 3 Segment Feature Extraction

### Objective

Extract fixed-length feature vectors from each high-dimensional time series segment.

The feature matrix will be used by the later clustering task to identify different operating conditions.

### Implementation Files

Added:

```text
src/feature_extractor.py
feature_extraction.py
```

`src/feature_extractor.py` contains the reusable feature extraction logic.

`feature_extraction.py` is the command line entry for extracting feature matrices from saved segmentation results.

### Input

The module uses:

```text
data/raw/ETTh1.csv
```

and segmentation result files:

```text
outputs/segmentation/method_a_ruptures.json
outputs/segmentation/method_b_window_stat.json
```

### Feature Categories

The implementation covers four required feature categories.

Statistical features:

```text
mean
standard deviation
skewness
kurtosis
25% quantile
50% quantile
75% quantile
```

Time-domain shape features:

```text
RMS
crest factor
waveform factor
zero-crossing rate
```

Trend features:

```text
linear fitting slope
mean of first-order difference
```

Correlation features:

```text
upper-triangular coefficients of the inter-channel correlation matrix
```

### Feature Dimension

For each of the 7 ETTh1 sensor variables, the module extracts 13 single-channel features:

```text
7 variables * 13 features = 91 features
```

For inter-channel correlation, the upper triangular part of the 7 by 7 correlation matrix contains:

```text
7 * 6 / 2 = 21 features
```

Therefore, each segment has:

```text
91 + 21 = 112 features
```

The saved CSV also includes three metadata columns:

```text
segment_start
segment_end
segment_length
```

So the final CSV column count is:

```text
112 + 3 = 115 columns
```

### Standardization

The feature matrix is standardized with:

```python
sklearn.preprocessing.StandardScaler
```

The command line also supports:

```text
--scaler minmax
```

for MinMax scaling.

### Command Line Usage

Extract features for both Method A and Method B:

```bash
python feature_extraction.py \
  --input data/raw/ETTh1.csv \
  --scaler standard
```

Default outputs:

```text
outputs/features/ruptures_pelt_features_raw.csv
outputs/features/ruptures_pelt_features_scaled.csv
outputs/features/ruptures_pelt_feature_metadata.json
outputs/features/window_stat_distance_features_raw.csv
outputs/features/window_stat_distance_features_scaled.csv
outputs/features/window_stat_distance_feature_metadata.json
```

### Verification Result

The command was executed successfully.

Method A feature matrix:

```text
method: ruptures_pelt
segments: 39
features: 112
raw shape: 39 x 115
scaled shape: 39 x 115
NaN count: 0
```

Method B feature matrix:

```text
method: window_stat_distance
segments: 33
features: 112
raw shape: 33 x 115
scaled shape: 33 x 115
NaN count: 0
```

This completes Task 3 feature extraction.

## 2026-09-01 - Task 4 Clustering and Operating Condition Identification

### Objective

Cluster segment-level feature vectors and identify operating conditions.

The task requires:

- Compare at least two clustering algorithms.
- Use clustering evaluation metrics to choose the cluster count `K`.
- Assign each cluster to an operating condition ID such as `OP_001`.
- Output each segment's condition ID.
- Output each condition's start time, end time, and duration statistics.

### Implementation Files

Added:

```text
src/clusterer.py
clustering.py
```

`src/clusterer.py` contains reusable clustering and operating-condition labeling logic.

`clustering.py` is the command line entry.

### Input

The clustering module uses the standardized feature matrices generated by Task 3:

```text
outputs/features/ruptures_pelt_features_scaled.csv
outputs/features/window_stat_distance_features_scaled.csv
```

The original ETTh1 CSV is also used to map segment indexes back to timestamps:

```text
data/raw/ETTh1.csv
```

### Algorithms

Two clustering algorithms are implemented:

```text
K-Means
Gaussian Mixture Model
```

For each feature matrix and each algorithm, the code evaluates candidate cluster counts:

```text
K = 2, 3, ..., 8
```

The selected `K` is the one with the highest Silhouette Score. If there is a tie, Calinski-Harabasz Index is used as the secondary criterion.

### Evaluation Metrics

Silhouette Score:

```text
higher is better
```

It measures whether samples are closer to their own cluster than to other clusters.

Calinski-Harabasz Index:

```text
higher is better
```

It measures the ratio between inter-cluster dispersion and intra-cluster dispersion.

### Operating Condition ID Mapping

Cluster labels produced by K-Means or GMM are arbitrary numeric labels. To make the output stable and readable, cluster labels are mapped to operating condition IDs:

```text
OP_001
OP_002
...
```

The mapping is sorted by each cluster's average segment start position. Earlier operating states receive smaller IDs.

### Duration Calculation

Segments are treated as half-open intervals:

```text
[segment_start, segment_end)
```

For hourly ETTh1 data, duration is computed by:

```text
duration_hours = end_time - start_time
```

where `end_time` is the timestamp at `segment_end`; for the final segment, it is estimated as the last timestamp plus one median time step.

This makes a segment containing 48 hourly records have a duration of 48 hours.

### Command Line Usage

Run clustering for both Method A and Method B feature matrices:

```bash
python clustering.py \
  --input data/raw/ETTh1.csv \
  --min-k 2 \
  --max-k 8
```

### Output Files

Overall algorithm comparison:

```text
outputs/clustering/algorithm_comparison.csv
```

Per feature method and algorithm:

```text
outputs/clustering/<feature_method>/<algorithm>/segment_conditions.csv
outputs/clustering/<feature_method>/<algorithm>/condition_summary.csv
outputs/clustering/<feature_method>/<algorithm>/clustering_metrics.json
```

`segment_conditions.csv` contains:

```text
segment_id
segment_start
segment_end
start_time
end_time
duration_hours
cluster_label
condition_id
```

`condition_summary.csv` contains:

```text
condition_id
segment_count
first_start_time
last_end_time
total_duration_hours
mean_duration_hours
min_duration_hours
max_duration_hours
```

### Verification Result

The command was executed successfully.

Algorithm comparison:

```text
feature_method          algorithm  selected_k  silhouette  calinski_harabasz
ruptures_pelt           kmeans     2           0.5738      9.82
ruptures_pelt           gmm        2           0.4638      6.64
window_stat_distance    kmeans     2           0.5315      7.89
window_stat_distance    gmm        2           0.0960      3.53
```

For the current feature matrices, K-Means performs better than GMM under both segmentation methods.

Generated condition assignment and summary files:

```text
outputs/clustering/ruptures_pelt/kmeans/segment_conditions.csv
outputs/clustering/ruptures_pelt/kmeans/condition_summary.csv
outputs/clustering/ruptures_pelt/gmm/segment_conditions.csv
outputs/clustering/ruptures_pelt/gmm/condition_summary.csv
outputs/clustering/window_stat_distance/kmeans/segment_conditions.csv
outputs/clustering/window_stat_distance/kmeans/condition_summary.csv
outputs/clustering/window_stat_distance/gmm/segment_conditions.csv
outputs/clustering/window_stat_distance/gmm/condition_summary.csv
```

This completes Task 4 clustering and operating condition identification.

## 2026-09-01 - Task 5 Interactive Visualization Dashboard

### Objective

Build an interactive frontend for visualizing segmentation, clustering, representative time series, and operating-condition timelines.

The frontend should follow the two design references:

```text
design/DESIGN_A.md
design/DESIGN_B.md
```

and provide two visual modes.

### Technology Path

Selected stack:

```text
React
Vite
TypeScript
Apache ECharts
CSS theme variables
```

Reason:

- React/Vite gives full layout and styling control.
- ECharts supports line charts, markLine, markArea, scatter plots, and custom timeline bars.
- CSS variables make it easy to switch between the Apple-like and Binance-like design modes.
- This route provides a stronger webpage feeling than Streamlit.

### Added Files

Frontend project:

```text
frontend/package.json
frontend/package-lock.json
frontend/index.html
frontend/vite.config.ts
frontend/tsconfig.json
frontend/src/main.tsx
frontend/src/styles.css
frontend/public/data/dashboard_data.json
```

Data preparation script:

```text
scripts/prepare_frontend_data.py
```

### Data Preparation

The frontend does not read all raw CSV and output files directly. Instead, the Python script prepares one compact JSON file:

```bash
python scripts/prepare_frontend_data.py
```

Output:

```text
frontend/public/data/dashboard_data.json
```

The JSON contains:

- sampled ETTh1 multichannel time series
- segmentation boundaries from Method A and Method B
- clustering assignments from K-Means and GMM
- PCA 2D coordinates for segment feature vectors
- cluster centers in the 2D projection
- representative segments for each operating condition
- condition duration summaries

### Two Design Modes

Apple Gallery:

```text
light canvas
quiet blue interaction color
large whitespace
minimal chrome
gallery-like layout
```

Binance Terminal:

```text
deep dark canvas
yellow primary accent
dense dashboard layout
dark data panels
financial-platform visual rhythm
```

The two modes share the same charts and data but use different CSS theme variables.

### Required Visualizations

The dashboard implements all four required visualizations.

Raw multichannel time series with segmentation boundaries:

```text
ECharts line chart
vertical dashed markLine for change points
alternating markArea backgrounds for segments
sensor visibility checkboxes
```

Clustering result scatter plot:

```text
PCA 2D feature projection
color by condition_id
diamond markers for cluster centers
algorithm switch between K-Means and GMM
```

Representative segment comparison:

```text
select 2 to 3 representative segments per condition
representatives selected by distance to cluster center
overlay representative time series in one coordinate system
sensor selector for comparison variable
```

Operating-condition timeline:

```text
custom ECharts range-bar timeline
time axis
color by condition_id
hover tooltip with start time, end time, and duration
```

### Interaction Design

Interactive controls include:

```text
design mode: Apple Gallery / Binance Terminal
segmentation method: Method A / Method B
clustering algorithm: K-Means / GMM
representative sensor selector
visible sensor checkboxes
tab navigation across four visualizations
```

### Verification

Frontend data preparation completed:

```text
Saved frontend data to frontend/public/data/dashboard_data.json
```

Production build completed:

```bash
cd frontend
npm run build
```

Result:

```text
vite build completed successfully
```

The local development server was started:

```bash
npm run dev -- --port 5173
```

Local URL:

```text
http://127.0.0.1:5173/
```

The page and data endpoint were verified with HTTP requests:

```text
GET / -> 200 OK
GET /data/dashboard_data.json -> returned dashboard metadata
```

This completes the first interactive implementation of Task 5.
