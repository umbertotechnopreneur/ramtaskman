# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### RAM이 어디에 쓰이는지 터미널에서 확인하세요.

ramtaskman은 Linux, Windows, macOS용 실험적인 메모리 모니터입니다. 여러 시스템의 메모리 사용을 복잡한 도구 없이 이해하고 싶다는 호기심과 연구에서 출발했습니다. Vibeware 프로젝트입니다.

![ramtaskman](../images/overview.png)

*Linux에서 실제 Textual 인터페이스를 합성 예시 데이터로 캡처했습니다. 스크린샷은 현재 이탈리아어 인터페이스입니다.*


![Multilingual dashboard](../images/multilingual.png)

*6개 언어로 부분 번역한 대시보드; Linux에서 합성 데이터로 캡처했습니다.*

## 주요 기능

1. 시스템 RAM, 사용 가능 메모리, 캐시와 기록 그래프를 한눈에 보고 Slim/전체 진단 모드를 선택합니다.
2. 앱과 프로세스를 살펴보고 사용 가능한 지표로 정렬하며 측정 범위를 확인합니다.
3. RSS와 USS를 확인하고, Linux에서는 PSS·스왑·SwapPSS도 살펴봅니다. 누락된 값은 명확히 표시합니다.
4. 이름, 실행 파일, 정확한 PID로 검색하고 사용자·스왑·부분 데이터로 필터링합니다.
5. Linux에서 프로세스 메모리 영역을 탐색합니다. Windows 가상 주소 보기는 실험적입니다.
6. 두 샘플을 비교하고 캡처를 로컬에 저장하거나 오프라인에서 다시 엽니다.

## 화면 살펴보기

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

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

주요 키: m 모드 전환, g 앱/프로세스 전환, / 검색, f 필터, d 상세, r 영역, ? 지표 설명, q 종료. 전체 기술 가이드는 현재 이탈리아어입니다.

`./run.sh --language ko`로 한국어 대시보드를 실행합니다(Windows: `.\run.cmd --language ko`). 번역은 부분적이며 상세 설명, 영역, 오류와 일부 제어는 이탈리아어 또는 영어로 남아 있습니다.

## 실험적 프로젝트: 수치를 신중히 해석하세요

측정은 순차적으로 이루어지고 권한에 따라 보이는 범위가 제한되며 앱 그룹화는 휴리스틱입니다. 누락 데이터는 0이 아닌 n/a입니다. RSS는 공유 페이지를 중복 계산할 수 있고 프로세스 PSS는 전체 RAM이 아닙니다. 캐시와 사용 가능 메모리는 겹칩니다. 프로세스 스왑은 commit에서 추정하지 않습니다.

Linux는 읽을 수 있을 때 PSS와 프로세스별 스왑을 제공합니다. 여기서는 Windows와 macOS에서 제공하지 않습니다. Linux 영역은 smaps를 사용하며 Windows는 실험적인 가상 범위만 표시하고 macOS 영역 지도는 아직 없습니다. 실제 하드웨어 검증은 Linux에서 수행했으며 Windows와 macOS는 검증이 필요합니다.

## 영감과 감사

영감을 준 Scott Hanselman과 GPU Taskman에 감사드립니다. ramtaskman은 프로젝트의 일부를 재사용하고 터미널 인터페이스를 RAM에 맞게 조정한 독립 프로젝트이며 공식 릴리스가 아닙니다. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

번역은 AI의 도움으로 작성했습니다. 번역가와 원어민의 수정 제안을 환영합니다.

[전체 기술 가이드(이탈리아어)](../guida.md) · [MIT 라이선스, 원본 저작권 유지.](../../LICENSE)
