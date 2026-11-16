# ramtaskman

[Italiano](../../README.md) · [English](README.en.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Entenda para onde vai a RAM, direto no terminal.

ramtaskman é um monitor experimental de memória para Linux, Windows e macOS. Nasceu da curiosidade e da pesquisa para entender a memória em diferentes sistemas sem recorrer a ferramentas complicadas. É um projeto Vibeware.

![ramtaskman](../images/overview.png)

*Interface Textual real capturada no Linux com dados sintéticos de demonstração. As imagens mostram a interface italiana atual.*


![Multilingual dashboard](../images/multilingual.png)

*Tradução parcial do painel em seis idiomas; capturas no Linux com dados sintéticos.*

## O que você pode fazer

1. Veja RAM, memória disponível, cache e histórico; escolha o modo Slim ou diagnóstico completo.
2. Explore aplicativos e processos, ordene métricas disponíveis e confira a cobertura das leituras.
3. Consulte RSS e USS; no Linux, também PSS, swap e SwapPSS, com detalhes e dados ausentes indicados.
4. Pesquise por nome, executável ou PID exato e filtre por usuário, swap ou dados parciais.
5. Explore regiões de memória no Linux; a visualização virtual do Windows é experimental.
6. Compare duas amostras e salve ou abra capturas locais, inclusive offline.

## Por dentro

![Full diagnostics](../images/full-diagnostics.png)

![Process regions](../images/regions-resident.png)

## Como começar

São necessários Python 3.11+ e uv. No Linux, são exigidos /proc e smaps_rollup. A primeira execução precisa de rede para instalar as dependências fixadas. Ambiente e cache ficam no projeto.

```bash
git clone https://github.com/umbertotechnopreneur/ramtaskman.git
cd ramtaskman
./run.sh
```

No Windows, na pasta do projeto e usando o Windows Terminal:

```powershell
.\run.cmd
```

Use --once ou --json para uma leitura única ou saída JSON. Não compartilhe .venv entre sistemas: recrie-o localmente. O projeto não está publicado no PyPI.

Atalhos: m troca o modo, g alterna aplicativos/processos, / pesquisa, f filtra, d mostra detalhes, r abre regiões, ? explica as métricas e q sai. O guia técnico completo está atualmente em italiano.

A tela principal pode ser aberta com `./run.sh --language pt` (Windows: `.\run.cmd --language pt`). A tradução é parcial: explicações detalhadas, regiões, erros e alguns controles permanecem em italiano ou inglês.

## Experimental: interprete os números com cuidado

As leituras são sequenciais, permissões podem limitar a visibilidade e o agrupamento de aplicativos é heurístico. Dados ausentes são n/a, não zero. RSS pode contar páginas compartilhadas mais de uma vez; PSS dos processos não é toda a RAM. Cache se sobrepõe à memória disponível. Swap por processo não é deduzida do commit.

Linux fornece PSS e swap por processo quando legíveis. Aqui elas não são expostas no Windows ou macOS. Regiões Linux usam smaps; no Windows são intervalos virtuais experimentais; no macOS o mapa ainda não existe. A verificação local em hardware foi feita no Linux; Windows e macOS precisam de validação nativa.

## Inspiração e agradecimentos

Obrigado a Scott Hanselman e ao GPU Taskman pela inspiração. ramtaskman reutiliza partes do projeto e adapta sua interface de terminal à RAM; é independente e não é uma versão oficial. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Traduções preparadas com ajuda de IA. Correções de tradutores e falantes nativos são bem-vindas.

[Guia técnico completo (italiano)](../guida.md) · [Licença MIT; copyright original preservado.](../../LICENSE)
