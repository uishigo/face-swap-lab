# face-swap-lab 使い方（headless-run）

セットアップ手順・既知の問題は [SETUP_AND_USAGE.md](SETUP_AND_USAGE.md) を参照。

```powershell
# ffmpeg と curl シムをPATHに追加してから実行する
$env:PATH = "$PWD;$env:PATH;$env:LOCALAPPDATA\Microsoft\WinGet\Links"

.\.venv\Scripts\python.exe facefusion.py headless-run `
  --execution-providers cpu `
  --processors face_swapper `
  -s .assets\source.jpg `
  -t .assets\target-240p.mp4 `
  -o .assets\output\swapped.mp4
```

- `-s`: ソース顔画像（合成したい顔）
- `-t`: ターゲット動画/画像（顔を置き換えられる側）
- `-o`: 出力先
- `--processors face_swapper`: 顔スワップ処理のみ実行（他に `face_enhancer`, `lip_syncer`, `frame_enhancer` など多数のプロセッサがある）
- `--execution-providers`: `cpu` / `directml` / `cuda` など。このマシンでは `cpu` のみ動作確認済み

初回実行時は必要なONNXモデル（顔検出・ランドマーク・スワップ本体など、計10種類程度）が `.assets/models/` に自動ダウンロードされる。

## 実測値（このマシン・CPU実行）

- 入力: 240p, 270フレーム（約10.8秒, 25fps）
- 処理時間: 約9.6分（1フレームあたり約2秒）
- 出力: h264, 426x226, 823KB

フレーム数・解像度が上がるとほぼ線形に処理時間が伸びる。DirectMLが正常に動けば大幅な高速化が期待できるが未解決（[SETUP_AND_USAGE.md](SETUP_AND_USAGE.md) の「既知の問題3」参照）。
