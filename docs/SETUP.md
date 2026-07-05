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

```powershell
# 1. FaceFusion をクローン（このディレクトリ自体が facefusion のクローン先）
git clone --depth 1 https://github.com/facefusion/facefusion.git .

# 2. venv 作成
python -m venv .venv

# 3. venv を「有効化した状態」でインストーラーを実行する（重要、下記の既知の問題1参照）
& .\.venv\Scripts\Activate.ps1
python install.py directml --skip-conda
# NVIDIA GPUがある場合は `cuda`、CPUのみなら `default` を指定する

# 4. ffmpeg（システムに未導入だったため winget でインストール）
winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
# インストール後、新しいシェルでPATHが反映される
```

### テスト素材

FaceFusion公式リポジトリのexampleアセット（source.jpg / target-240p.mp4）を `.assets/` に配置して動作確認に使用。

```powershell
Invoke-WebRequest -Uri "https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/source.jpg" -OutFile ".assets\source.jpg"
Invoke-WebRequest -Uri "https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/target-240p.mp4" -OutFile ".assets\target-240p.mp4"
```

## 既知の問題と対処

### 1. venvを有効化せずにインストーラーを実行すると、パッケージがグローバルPythonに入る

`install.py` は内部で `shutil.which('pip')` を使ってパッケージをインストールする。これは **PATH上のpip** を解決するため、venvを「有効化」していない状態（`.\.venv\Scripts\python.exe install.py ...` のように直接実行するだけ）だと、システム側のグローバルpipが使われてしまい、venv内には何もインストールされない。

**対処**: 必ず `& .\.venv\Scripts\Activate.ps1` で venv を有効化してから `python install.py ...` を実行する。

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

## 使い方

実行手順は [USAGE.md](USAGE.md) に分離した。

## 次のステップの選択肢

- DirectMLハングの原因調査（解決すれば大幅高速化）
- 別の顔・動画素材で品質を検証
- 品質に満足できない場合、DeepFaceLab型（対象の顔で個別学習するモデル）への移行を検討
