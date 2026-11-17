# ramtaskman

[Italiano](README.it.md) · [English](../../README.md) · [中文（简体）](README.zh.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Tiếng Việt](README.vi.md) · [Español](README.es.md) · [Português](README.pt.md) · [Deutsch](README.de.md) · [日本語](README.ja.md)

### Entenda para onde vai a RAM, direto no terminal.

ramtaskman é um monitor experimental de memória desenvolvido e testado no Linux e no Windows. Nasceu da curiosidade e da pesquisa para entender a memória em diferentes sistemas sem recorrer a ferramentas complicadas. É um projeto [VibeWare](https://umbertogiacobbi.biz/vibeware/manifesto).

Também existe um backend experimental para macOS. Não temos um Mac, por isso ainda não o testamos nem validamos. Nossos testes e a CI abrangem Linux e Windows.

[Documentação](../README.md) · [Contribuir](../../CONTRIBUTING.md) · [MIT](../../LICENSE)

![ramtaskman](../images/cover.png)

*Interface Textual real capturada no Linux com dados sintéticos. A capa mostra um recorte do painel e da tabela; a interface apresentada está em inglês.*

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

Atalhos: m troca o modo, g alterna aplicativos/processos, / pesquisa, f filtra, d mostra detalhes, r abre regiões, ? explica as métricas e q sai. O guia técnico completo está atualmente em inglês.

Abra a tela principal com `./run.sh --language pt` (Windows: `.\run.cmd --language pt`). Os textos do aplicativo estão disponíveis em dez idiomas: `--language` seleciona o idioma da interface, do rodapé, da ajuda, da CLI e do relatório de texto `--once`. As mensagens técnicas produzidas pelo aplicativo também são traduzidas. Os identificadores e o esquema JSON permanecem estáveis; os detalhes do sistema operacional e os textos das capturas salvas mantêm o idioma original. A verificação local abrange Linux com Python 3.14.4: interface sintética em 160×48 e 80×24, CLI, construção de pacotes, instalação isolada e replay. As verificações do Windows são executadas na CI; o macOS está excluído das verificações do projeto. As traduções ainda aguardam revisão de falantes nativos.

## O que você pode fazer

1. Veja RAM, memória disponível, cache e histórico; escolha o modo Slim ou diagnóstico completo.
2. Explore aplicativos e processos, ordene métricas disponíveis e confira a cobertura das leituras.
3. Consulte RSS e USS; no Linux, também PSS, swap e SwapPSS, com detalhes e dados ausentes indicados.
4. Pesquise por nome, executável ou PID exato e filtre por usuário, swap ou dados parciais.
5. Explore regiões de memória no Linux; a visualização virtual do Windows é experimental.
6. Compare duas amostras e salve ou abra capturas locais, inclusive offline.

## Por dentro

![Full diagnostics](../images/full-diagnostics.png)

[Galeria](../images/README.md) · [A/B](../images/regions-comparison.png) · [10 languages](../images/multilingual.png)

## Valor da RAM e divisão mensal

```bash
./run.sh --ram-price 320 --ram-currency EUR --ram-months 36
```

Informe o preço de toda a RAM: não há consulta de preços nem solicitação de rede. A capacidade padrão é a visível ao sistema; use `--ram-capacity-gib 32` para um kit nominal de 32 GiB. Valor = preço × bytes atribuíveis / capacidade. `--ram-months` divide esse valor do hardware pelo número de meses escolhido: não é uma conta, consumo de energia, média mensal ou economia garantida. Linux usa PSS; Windows usa USS, somente memória privada residente. Não há substituição por RSS. Grupos incompletos permanecem n/a (`null` no JSON). Não some aplicativos aos seus processos nem à memória do sistema. As amostras são sequenciais, não atômicas. JSON inclui `ram_valuation` somente quando solicitado. F1 abre as informações e os créditos; Esc retorna ao monitor.

## Experimental: interprete os números com cuidado

As leituras são sequenciais, permissões podem limitar a visibilidade e o agrupamento de aplicativos é heurístico. Dados ausentes são n/a, não zero. RSS pode contar páginas compartilhadas mais de uma vez; PSS dos processos não é toda a RAM. Cache se sobrepõe à memória disponível. Swap por processo não é deduzida do commit.

Linux fornece PSS e swap por processo quando legíveis. Aqui elas não são expostas no Windows nem no backend experimental do macOS. Regiões Linux usam smaps; no Windows são intervalos virtuais experimentais; no macOS o mapa ainda não existe. As verificações do projeto abrangem Linux local e Windows em CI nativa; o macOS permanece fora desse escopo.

A verificação manual em um PC Windows pessoal ainda está pendente.

## Use, modifique e compartilhe

Você pode usar, copiar, modificar e redistribuir ramtaskman, inclusive comercialmente, sob a [licença MIT](../../LICENSE). Preserve os avisos de copyright e permissão nas cópias ou partes substanciais. O software é fornecido sem garantias. Contribuições e correções de tradução são bem-vindas; as dependências mantêm suas próprias licenças.

[Contribuir](../../CONTRIBUTING.md) · [Atribuições de terceiros](../../THIRD_PARTY_NOTICES.md)

## Inspiração e agradecimentos

Obrigado a Scott Hanselman e ao GPU Taskman pela inspiração. ramtaskman reutiliza partes do projeto e adapta sua interface de terminal à RAM; é independente e não é uma versão oficial. [Scott Hanselman](https://github.com/shanselman) · [GPU Taskman](https://github.com/shanselman/gputaskman) · [Provenance](../upstream.md)

Traduções preparadas com ajuda de IA. Correções de tradutores e falantes nativos são bem-vindas.

[Guia técnico completo (inglês)](../guida.md) · [Licença MIT; copyright original preservado.](../../LICENSE)
