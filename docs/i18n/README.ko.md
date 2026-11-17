# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### RAM이 어디에 쓰이는지 터미널에서 확인하세요.

ramtaskman은 Linux와 Windows에서 개발하고 테스트하는 실험적인 메모리 모니터입니다. 여러 시스템의 메모리 사용을 복잡한 도구 없이 이해하고 싶다는 호기심과 연구에서 출발했습니다. [VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto) 프로젝트입니다.

실험적인 macOS 백엔드도 있습니다. Mac이 없어서 아직 테스트하거나 검증하지 못했습니다. 프로젝트의 테스트와 CI는 Linux와 Windows에서 진행합니다.

[문서](../README.md) · [기여하기](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Linux에서 합성 데이터로 캡처한 실제 Textual 화면입니다. 표지는 대시보드와 표의 일부이며, 예시 인터페이스는 영어입니다.*

## 시작하기

Python 3.11 이상과 uv가 필요합니다. Linux에는 /proc와 smaps_rollup이 필요합니다. 첫 실행 시 고정된 의존성 설치에 네트워크가 필요하며 환경과 캐시는 프로젝트 폴더에 유지됩니다.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

Windows Terminal에서 프로젝트 폴더로 이동한 후 실행하세요:

```powershell
.\run.cmd
```

--once는 단일 측정, --json은 JSON 출력을 제공합니다. 운영체제 간 .venv를 공유하지 말고 로컬에서 다시 만드세요. PyPI에는 게시되지 않았습니다.

주요 키: m 모드 전환, g 앱/프로세스 전환, / 검색, f 필터, d 상세, r 영역, ? 지표 설명, q 종료. 전체 기술 가이드는 현재 영어입니다.

`./run.sh --language ko`로 한국어 대시보드를 실행합니다(Windows: `.\run.cmd --language ko`). 앱 텍스트는 10개 언어로 제공되며, `--language`로 인터페이스, 바닥글, 도움말, CLI와 `--once` 텍스트 보고서의 언어를 선택합니다. 앱 자체에서 생성하는 기술 메시지도 번역했습니다. 식별자와 JSON 스키마는 안정적으로 유지하며, 운영체제 세부 정보와 저장된 캡처의 텍스트는 원래 언어를 유지합니다. 로컬 검증 범위는 Linux와 Python 3.14.4이며 합성 데이터 UI 160×48 및 80×24, CLI, 빌드, 격리 설치와 재생을 포함합니다. Windows는 CI에서 확인하며 macOS는 프로젝트 검증 대상에서 제외합니다. 원어민의 번역 검토가 여전히 필요합니다.

## 주요 기능

1. 시스템 RAM, 사용 가능 메모리, 캐시와 기록 그래프를 한눈에 보고 Slim/전체 진단 모드를 선택합니다.
2. 앱과 프로세스를 살펴보고 사용 가능한 지표로 정렬하며 측정 범위를 확인합니다.
3. RSS와 USS를 확인하고, Linux에서는 PSS·스왑·SwapPSS도 살펴봅니다. 누락된 값은 명확히 표시합니다.
4. 이름, 실행 파일, 정확한 PID로 검색하고 사용자·스왑·부분 데이터로 필터링합니다.
5. Linux에서 프로세스 메모리 영역을 탐색합니다. Windows 가상 주소 보기는 실험적입니다.
6. 두 샘플을 비교하고 캡처를 로컬에 저장하거나 오프라인에서 다시 엽니다.

## 화면 살펴보기

![Full diagnostics](../images/full-diagnostics.png)

[이미지 모음](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## RAM 가치와 월별 배분

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

전체 RAM의 가격을 직접 입력합니다. 가격 조회나 네트워크 요청은 없습니다. 기본 용량은 운영체제에 보이는 RAM이며, 정격 32 GiB 키트는 `--ram-capacity-gib 32`로 지정합니다. 가치 = 가격 × 귀속 가능한 바이트 / 용량입니다. `--ram-months`는 이 하드웨어 가치를 선택한 개월 수로 나눕니다. 청구액, 에너지 소비, 월평균 또는 보장된 절약액이 아닙니다. Linux는 PSS를, Windows는 개인 상주 메모리만 나타내는 USS를 사용하며 RSS로 대체하지 않습니다. 불완전한 그룹은 n/a(JSON에서는 `null`)입니다. 앱과 그 구성 프로세스 또는 시스템 메모리를 중복 합산하지 마세요. 샘플은 순차적이며 원자적이지 않습니다. JSON은 요청할 때만 `ram_valuation`을 포함합니다. F1은 정보와 크레딧을 열고 Esc는 모니터링으로 돌아갑니다.

## 실험적 프로젝트: 수치를 신중히 해석하세요

측정은 순차적으로 이루어지고 권한에 따라 보이는 범위가 제한되며 앱 그룹화는 휴리스틱입니다. 누락 데이터는 0이 아닌 n/a입니다. RSS는 공유 페이지를 중복 계산할 수 있고 프로세스 PSS는 전체 RAM이 아닙니다. 캐시와 사용 가능 메모리는 겹칩니다. 프로세스 스왑은 commit에서 추정하지 않습니다.

Linux는 읽을 수 있을 때 PSS와 프로세스별 스왑을 제공합니다. 여기서는 Windows와 실험적인 macOS 백엔드에서 제공하지 않습니다. Linux 영역은 smaps를 사용하며 Windows는 실험적인 가상 범위만 표시하고 macOS 영역 지도는 아직 없습니다. 프로젝트 검증에는 로컬 Linux 확인과 네이티브 Windows CI 확인이 포함되며 macOS는 그 범위에서 제외합니다.

개인 Windows PC에서의 수동 검증은 아직 남아 있습니다.

## 사용, 수정, 공유

[MIT 라이선스](../../LICENSE)에 따라 ramtaskman을 사용, 복사, 수정, 재배포할 수 있으며 상업적 이용도 가능합니다. 사본이나 상당 부분에 저작권 및 허가 고지를 유지하세요. 소프트웨어는 보증 없이 제공됩니다. 기여와 번역 수정을 환영하며, 의존성은 각각의 라이선스를 유지합니다.

[기여하기](../../CONTRIBUTING.md) · [제3자 고지](../../THIRD_PARTY_NOTICES.md)

## 영감과 감사

영감을 준 Scott Hanselman과 GPU Taskman에 감사드립니다. ramtaskman은 프로젝트의 일부를 재사용하고 터미널 인터페이스를 RAM에 맞게 조정한 독립 프로젝트이며 공식 릴리스가 아닙니다. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

번역은 AI의 도움으로 작성했습니다. 번역가와 원어민의 수정 제안을 환영합니다.

[전체 기술 가이드(영어)](../guida.md) · [MIT 라이선스, 원본 저작권 유지.](../../LICENSE)
