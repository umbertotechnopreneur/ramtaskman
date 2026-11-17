# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### RAMの使い道を、ターミナルから見渡す。

ramtaskmanはLinuxとWindowsで開発・テストしている実験的なメモリモニターです。さまざまなシステムのメモリを、複雑なツールに頼らず理解したいという好奇心と研究から生まれた[VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto)プロジェクトです。

実験的なmacOSバックエンドもあります。手元にMacがないため、まだテストも検証もできていません。プロジェクトのテストとCIはLinuxとWindowsで行っています。

[ドキュメント](../README.md) · [貢献する](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Linux上で合成データを使って撮影した実際のTextual画面です。表紙はダッシュボードと表の一部を切り出しており、表示例の言語は英語です。*

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

主なキー: m モード切替、g アプリ/プロセス切替、/ 検索、f フィルター、d 詳細、r 領域、? 指標の説明、q 終了。完全な技術ガイドは現在英語です。

`./run.sh --language ja`で日本語のダッシュボードを起動します（Windows: `.\run.cmd --language ja`）。アプリのテキストは10言語に対応しており、`--language`で画面、フッター、ヘルプ、CLI、`--once`のテキストレポートの言語を選択できます。アプリが生成する技術メッセージも翻訳しています。識別子とJSONスキーマは安定したまま維持し、OSの詳細情報や保存済みキャプチャのテキストは元の言語を保持します。ローカル検証の対象はLinuxとPython 3.14.4で、160×48および80×24の合成データUI、CLI、ビルド、隔離環境へのインストールと再生を含みます。WindowsはCIで確認し、macOSはプロジェクトの検証対象外です。翻訳は引き続き母語話者によるレビューが必要です。

## 主な機能

1. システムRAM、利用可能メモリ、キャッシュ、履歴を一覧表示し、Slimと詳細診断を切り替えます。
2. アプリとプロセスを調べ、利用可能な指標で並べ替え、測定のカバー範囲を確認します。
3. RSSとUSSを確認し、LinuxではPSS、スワップ、SwapPSSも表示します。欠損値は明示します。
4. 名前、実行ファイル、正確なPIDで検索し、ユーザー、スワップ、部分データで絞り込みます。
5. Linuxでプロセスのメモリ領域を探索します。Windowsの仮想アドレス表示は実験的です。
6. 2つのサンプルを比較し、キャプチャをローカルに保存してオフラインでも開けます。

## 画面を見る

![Full diagnostics](../images/full-diagnostics.png)

[ギャラリー](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## RAMの価値と月ごとの配分

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

RAM全体の価格を自分で入力します。価格検索やネットワーク要求は行いません。既定の容量はOSから見えるRAMです。公称32 GiBのキットには `--ram-capacity-gib 32` を指定できます。価値 = 価格 × 帰属可能なバイト数 / 容量。`--ram-months` はこのハードウェア価値を指定月数で割ります。請求額、消費電力、月平均、保証された節約額ではありません。LinuxはPSS、Windowsはプライベート常駐メモリのみを表すUSSを使い、RSSへの代替はありません。不完全なグループはn/a（JSONでは `null`）です。アプリと構成プロセス、またはシステムメモリを重複して合計しないでください。測定は順次行われ、アトミックではありません。JSONには要求時のみ `ram_valuation` が追加されます。F1で情報とクレジットを開き、Escで監視に戻ります。

## 実験的プロジェクト: 数値は慎重に解釈してください

測定は順次行われ、権限によって表示範囲が制限されることがあります。アプリのグループ化はヒューリスティックです。欠損値はゼロではなくn/aです。RSSは共有ページを重複計上する場合があり、プロセスのPSSはシステム全体のRAMではありません。キャッシュは利用可能メモリと重複します。commitからプロセスのスワップを推定しません。

Linuxでは読み取り可能な場合にPSSとプロセス別スワップを提供します。Windowsと実験的なmacOSバックエンドではここに表示されません。Linuxの領域はsmapsを使用し、Windowsは実験的な仮想範囲のみ、macOSの領域マップは未実装です。プロジェクトの検証範囲はローカルのLinuxとネイティブWindows CIでの確認であり、macOSは対象外です。

個人のWindows PCでの手動検証は未実施です。

## 使用・変更・共有

[MITライセンス](../../LICENSE)に従い、商用を含めramtaskmanを使用、複製、変更、再配布できます。複製または実質的な部分に著作権表示と許諾表示を残してください。ソフトウェアは無保証で提供されます。貢献や翻訳修正を歓迎します。依存パッケージにはそれぞれのライセンスが適用されます。

[貢献する](../../CONTRIBUTING.md) · [サードパーティの表記](../../THIRD_PARTY_NOTICES.md)

## インスピレーションと感謝

インスピレーションを与えてくれたScott HanselmanとGPU Taskmanに感謝します。ramtaskmanはその一部を再利用し、ターミナルUIをRAM向けに調整した独立プロジェクトであり、公式リリースではありません。 [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

翻訳はAIの支援を受けて作成しました。翻訳者や母語話者による修正を歓迎します。

[技術ガイド全文（英語）](../guida.md) · [MITライセンス。元の著作権表示を保持しています。](../../LICENSE)
