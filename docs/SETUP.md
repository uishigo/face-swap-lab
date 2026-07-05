# face-swap-lab セットアップ・既知の問題・使い方

技術学習/検証目的で、AIによる顔スワップ(deepfake型)動画生成を試すためのプロジェクト。
本体は [FaceFusion](https://github.com/facefusion/facefusion)（`s0md3v/roop` の後継として現在も活発にメンテされている実装）をそのままクローンして使用している。

## 目的・利用範囲

- 学習・技術検証が目的。実用アプリ化やプロダクション利用は前提としていない。
- 他者の顔を無断で合成しない。テストには公開されているサンプル素材（FaceFusion公式のexampleアセット）を使用する。

## 環境

- OS: Windows 11
- GPU: Intel Arc 140V（NVIDIA CUDA非対応。DirectML/DirectX12経路の対象）
- Python: 3.12（`.venv` に仮想環境を作成して使用）

## セットアップ手順

> FaceFusion本体のソース（`facefusion/`配下など）はこのリポジトリに取り込み済みでgit管理下にあるため、**別環境でセットアップする場合は本リポジトリを`git clone`するだけでよく、FaceFusion本体を別途cloneする必要はない**。以下の「1」は初回構築時にこのリポジトリを作った際の手順の記録。

```powershell
# 1. (初回構築時のみ実施済み) FaceFusion をクローン（このディレクトリ自体が facefusion のクローン先）
# git clone --depth 1 https://github.com/facefusion/facefusion.git .

# 2. venv 作成（.gitignoreで除外されているため、別環境では毎回作り直しが必要）
python -m venv .venv

# 3. venv を「有効化した状態」でインストーラーを実行する（重要、下記の既知の問題1参照）
.\.venv\Scripts\Activate.ps1
python install.py directml --skip-conda
# NVIDIA GPUがある場合は `cuda`、CPUのみなら `default` を指定する

# 4. ffmpeg（システムに未導入だったため winget でインストール）
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
# インストール後、新しいシェルでPATHが反映される
```

### Macでの手順（参考、未検証）

このリポジトリはWindows環境で構築したが、macOSで動かす場合は主に以下3点が異なる。

```bash
# 2. venv作成
python3 -m venv .venv

# 3. venvを有効化してインストーラーを実行
source .venv/bin/activate
python install.py default --skip-conda

# 4. ffmpeg
brew install ffmpeg
```

- **`.venv\Scripts\Activate.ps1` ではなく `.venv/bin/activate` を使う**（拡張子なしのシェルスクリプト）。
- **`install.py` に指定できるのは `default` のみ**: [facefusion/installer.py](../facefusion/installer.py)の`ONNXRUNTIME_SET`は`is_windows()`/`is_linux()`で分岐しており、macOS（Darwin）向けの分岐が存在しない。そのため`directml`は選べず（Windows専用）、`coreml`もこのバージョンのfacefusionには未実装で選択肢に無い。結果としてCPU版onnxruntime（`default`）一択になり、Apple SiliconのGPU/Neural Engineは利用できない。
- 既知の問題2（`curl.exe`が社内ネットワークでハングする件）はWindows環境固有の事象のため、Macでは発生しない可能性が高い（未検証。もし発生する場合は同様に[curl_shim.py](../curl_shim.py)を流用できる）。

### テスト素材

FaceFusion公式リポジトリのexampleアセット（source.jpg / target-240p.mp4）を `.assets/` に配置して動作確認に使用。

```powershell
Invoke-WebRequest -Uri "https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/source.jpg" -OutFile ".assets\source.jpg"
Invoke-WebRequest -Uri "https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/target-240p.mp4" -OutFile ".assets\target-240p.mp4"
```

## 既知の問題と対処

### 1. venvを有効化せずにインストーラーを実行すると、パッケージがグローバルPythonに入る

`install.py` は内部で `shutil.which('pip')` を使ってパッケージをインストールする。これは **PATH上のpip** を解決するため、venvを「有効化」していない状態（`.\.venv\Scripts\python.exe install.py ...` のように直接実行するだけ）だと、システム側のグローバルpipが使われてしまい、venv内には何もインストールされない。

**対処**: 必ず `.\.venv\Scripts\Activate.ps1` で venv を有効化してから `python install.py ...` を実行する。

### 2. curl.exe がこの環境で外部HTTPS通信に対して完全にハングする

FaceFusionはモデルファイルのダウンロードを Python の `requests`/`urllib` ではなく、**システムの `curl` コマンドをサブプロセスで呼び出す実装**（[facefusion/curl_builder.py](../facefusion/curl_builder.py), [facefusion/download.py](../facefusion/download.py)）にしている。

このマシンでは Windows 標準の `C:\Windows\System32\curl.exe` が、huggingface.co や google.com など任意のホストへのHTTPS/HTTP通信で **応答が返らずハングする**（IPv4強制、TLS 1.2固定、`--connect-timeout`/`--max-time` を指定しても効果なし。DNS解決自体も怪しい挙動）。一方で以下は問題なく動作する。

- PowerShell の `Invoke-WebRequest`（.NET/WinHTTPスタック）
- Python の `urllib.request`

原因は特定できていないが、恐らく社内ネットワーク環境のセキュリティ製品によるプロセス単位のフィルタリングと推測される（一般的なネットワーク遮断ではなく、`curl.exe` という特定プロセスからの通信のみ影響を受ける）。

**対処**: `urllib` を使った `curl` の代替コマンド（シム）を作成し、`shutil.which('curl')` がそちらを解決するようにPATHの先頭に配置した。

- [curl_shim.py](../curl_shim.py) — facefusionが使う `curl` の引数（`-I`, `--create-dirs`, `--continue-at -`, `--output`, `--connect-timeout`, `--retry` など）の subset を実装し、`urllib.request` で代替
- [curl.cmd](../curl.cmd) — `curl_shim.py` をvenvのPythonで呼び出すラッパー。プロジェクトルートに配置し、実行時にプロジェクトルートをPATHの先頭に追加することで、System32のcurl.exeより先に解決される

この対処により、モデルファイル（`.assets/models/*.onnx`、11ファイル）のダウンロードとフェイススワップ処理が正常に完了することを確認済み。

### 3. DirectML(`--execution-providers directml`)実行がハングする（未解決）

Intel Arc GPU向けに `onnxruntime-directml` をインストールし `--execution-providers directml` で実行したところ、セッション初期化以降 **CPU使用率ほぼ0%・ネットワーク接続もなし** の状態で20分以上進行しなかった。curl問題を修正した後も同様の症状。

現時点では原因未特定（DirectMLのシェーダーコンパイルがこのGPU/ドライバで極端に遅い、またはハングしている可能性が高い）。**動作確認は `--execution-providers cpu` で行っている。**

今後調査するなら:
- GPUドライバの更新
- `onnxruntime-directml` のバージョン変更
- 単一フレーム・小さいモデルだけで最小再現を試す

### 4. 別のWindows環境で `Activate.ps1` が実行ポリシーによりブロックされる

別のWindows環境でセットアップ手順3（`.\.venv\Scripts\Activate.ps1`）を実行すると、以下のようなエラーになることがある。

```
このシステムではスクリプトの実行が無効になっているため、ファイル ...\Activate.ps1 を読み込むことができません。
```

PowerShellの実行ポリシー（Execution Policy）が既定で`Restricted`（スクリプト実行禁止）になっているのが原因。`.ps1`はスクリプトのため対象になるが、`.exe`や`.cmd`は影響を受けない。

**対処**: 現在のユーザーに対して実行ポリシーを緩める（管理者権限不要）。

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

確認プロンプトが出たら`Y`で許可。これでローカルスクリプト（`Activate.ps1`など）が実行可能になる（ネットワーク経由でダウンロードした未署名スクリプトには引き続き警告が出る）。そのシェルセッション限定で一時的に許可したいだけであれば、`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`でも代用可能（ウィンドウを閉じると設定は戻る）。

### 5. Macで `opencv-python==4.13.0.92` が見つからずインストールに失敗する（macOSバージョンが古い場合）

`pip install -r requirements.txt`（`install.py`経由）実行時に以下のようなエラーになることがある。

```
ERROR: Could not find a version that satisfies the requirement opencv-python==4.13.0.92 (from versions: ...)
ERROR: No matching distribution found for opencv-python==4.13.0.92
```

[requirements.txt](../requirements.txt)にピン留めされている`opencv-python==4.13.0.92`は、macOS向けwheelにOSの最小バージョン要件があり（Apple Silicon: macOS 13.0以上、Intel: macOS 14.0以上）、ソース配布（sdist）が無いため、これを下回るmacOSでは「一致するバージョンが無い」というエラーになる。[install.py](../install.py)で`SYSTEM_VERSION_COMPAT=0`を設定済みなので、古いPythonがOSバージョンを偽装して報告する類の問題ではなく、実際のmacOSバージョンがこのwheelの要求を満たしていないことが原因。

**対処**: `sw_vers -productVersion` で実際のmacOSバージョンを確認した上で、[requirements.txt](../requirements.txt)の`opencv-python`のバージョン指定を、そのmacOSバージョンでもwheelが提供されているバージョンまで下げる（例: `4.9.0.80`はarm64がmacOS 11.0以上、x86_64がmacOS 10.16以上まで対応）。facefusionが使うのは基本的な画像処理APIのみのため、4.x系内でのバージョン差による支障は基本的に無い。書き換え後に`python install.py default --skip-conda`を再実行すればセットアップが完了する。

## 使い方

実行手順は [USAGE.md](USAGE.md) に分離した。

## 次のステップの選択肢

- DirectMLハングの原因調査（解決すれば大幅高速化）
- 別の顔・動画素材で品質を検証
- 品質に満足できない場合、DeepFaceLab型（対象の顔で個別学習するモデル）への移行を検討
