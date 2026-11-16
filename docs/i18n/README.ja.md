# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### RAMの使い道を、ターミナルから見渡す。

ramtaskmanはLinux、Windows、macOS向けの実験的なメモリモニターです。さまざまなシステムのメモリを、複雑なツールに頼らず理解したいという好奇心と研究から生まれたVibewareプロジェクトです。

![ramtaskman](../images/overview.png)

*Linux上の実際のTextual画面を、合成したデモデータで撮影しています。画像は現在のイタリア語UIです。*


![Multilingual dashboard](../images/multilingual.png)

*6言語に部分翻訳したダッシュボード。Linux上で合成データを使って撮影しました。*

## 主な機能

1. システムRAM、利用可能メモリ、キャッシュ、履歴を一覧表示し、Slimと詳細診断を切り替えます。
2. アプリとプロセスを調べ、利用可能な指標で並べ替え、測定のカバー範囲を確認します。
3. RSSとUSSを確認し、LinuxではPSS、スワップ、SwapPSSも表示します。欠損値は明示します。
4. 名前、実行ファイル、正確なPIDで検索し、ユーザー、スワップ、部分データで絞り込みます。
5. Linuxでプロセスのメモリ領域を探索します。Windowsの仮想アドレス表示は実験的です。
6. 2つのサンプルを比較し、キャプチャをローカルに保存してオフラインでも開けます。

## 画面を見る

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

## 使い始める

Python 3.11以上とuvが必要です。Linuxでは/procとsmaps_rollupが必要です。初回は固定された依存関係のインストールにネットワークが必要です。環境とキャッシュはプロジェクト内に置かれます。

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

WindowsではプロジェクトフォルダーのWindows Terminalから実行します:

```powershell
.\run.cmd
```

--onceは1回の測定、--jsonはJSON出力です。.venvをOS間で共有せず、各環境で作り直してください。PyPIには公開していません。

主なキー: m モード切替、g アプリ/プロセス切替、/ 検索、f フィルター、d 詳細、r 領域、? 指標の説明、q 終了。完全な技術ガイドは現在イタリア語です。

`./run.sh --language ja`で日本語のダッシュボードを起動します（Windows: `.\run.cmd --language ja`）。翻訳は一部のみで、詳細説明、領域、エラー、一部の操作はイタリア語または英語のままです。

## 実験的プロジェクト: 数値は慎重に解釈してください

測定は順次行われ、権限によって表示範囲が制限されることがあります。アプリのグループ化はヒューリスティックです。欠損値はゼロではなくn/aです。RSSは共有ページを重複計上する場合があり、プロセスのPSSはシステム全体のRAMではありません。キャッシュは利用可能メモリと重複します。commitからプロセスのスワップを推定しません。

Linuxでは読み取り可能な場合にPSSとプロセス別スワップを提供します。WindowsとmacOSではここに表示されません。Linuxの領域はsmapsを使用し、Windowsは実験的な仮想範囲のみ、macOSは未実装です。実機検証はLinuxで実施済みで、WindowsとmacOSは別途必要です。

## インスピレーションと感謝

インスピレーションを与えてくれたScott HanselmanとGPU Taskmanに感謝します。ramtaskmanはその一部を再利用し、ターミナルUIをRAM向けに調整した独立プロジェクトであり、公式リリースではありません。 [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

翻訳はAIの支援を受けて作成しました。翻訳者や母語話者による修正を歓迎します。

[技術ガイド全文（イタリア語）](../guida.md) · [MITライセンス。元の著作権表示を保持しています。](../../LICENSE)
