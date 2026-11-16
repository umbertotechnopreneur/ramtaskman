# ramtaskman · como interpretar os números

Desenvolvemos e testamos no Linux e no Windows. O backend do macOS é experimental e não foi testado nem validado pelo projeto, pois não temos um Mac disponível. Eventuais verificações do macOS dependem de contribuições externas; a CI do projeto não inclui o macOS.

A estrutura visual do gputaskman, adaptada à memória no Linux, Windows e macOS.

| Campo | Significado |
|---|---|
| PSS | RAM privada mais uma parcela proporcional das páginas compartilhadas |
| USS | Private_Clean + Private_Dirty: páginas residentes privadas |
| RSS | Páginas residentes, incluindo compartilhadas; a soma pode contá-las várias vezes |
| Swap | Swap de smaps_rollup, sem swap shmem; pode contar páginas compartilhadas várias vezes |
| SwapPSS | Parcela proporcional da swap compartilhada contabilizada por smaps_rollup |
| RAM used | MemTotal − MemAvailable; não é a soma dos processos |
| Cache | Cached + Buffers + SReclaimable − Shmem; sobrepõe-se à memória disponível |
| PSI some | Percentual de tempo com pelo menos uma tarefa esperando memória, média de 10 s |

**Barra RAM:** usa toda a largura e divide os contadores Linux em memória anônima, cache de arquivos (Cached − Shmem), compartilhada/tmpfs, buffers, slab recuperável/não recuperável, outro (resíduo calculado) e livre. São categorias contábeis: a ordem não representa endereços físicos. Memória disponível é um indicador separado que inclui cache recuperável, portanto não é outro segmento. Detalhes clean/dirty e PSS do processo ficam em **d**, pois se sobrepõem aos contadores globais. Se faltam campos ou a amostra é inconsistente, a barra mostra em uso/disponível e informa por que falta a divisão. A legenda inclui categorias menores que um caractere.

**Barra USS dos apps:** os 10 primeiros apps com USS completa e os demais apps completos. A escala é a soma USS apenas dos apps completos da amostra, não toda a RAM. Números e cores correspondem à legenda. Grupos parciais são excluídos e a cobertura é declarada. O agrupamento segue a tabela; os segmentos não são endereços físicos.

**Windows/macOS:** USS e RSS vêm do psutil; PSS, Swap e SwapPSS por processo não são expostos e ficam n/a. No Windows, commit privado/pagefile NÃO é swap em disco. No macOS, RAM used é total − available do psutil, não a pressão de memória do Activity Monitor.

**Aplicativo:** no Linux um cgroup systemd explícito identifica a instância do app, incluindo auxiliares com executáveis diferentes. Usuários e instâncias distintos permanecem separados. Sem essa identidade, inclusive no Windows/macOS, o agrupamento usa usuário + executável ou, se o caminho não é legível, usuário + nome como heurística. O inspetor mostra o método.

**Busca e filtros:** **/** busca nome, executável ou PID exato; **f** seleciona usuário e estado de memória (**com swap** ou **dados parciais**). Filtros se combinam. Um app corresponde se um processo satisfaz a busca ou estado, mas seu total mantém todos os membros. Os filtros permanecem na vista de processos. Aplicam-se antes do Top 30; gráficos e painel descrevem todo o sistema. **Enter** na busca retorna à tabela. **Esc** nos controles ou **Reset** limpa filtros; **Esc** na tabela de processos volta aos apps mantendo-os. Dados parciais considera apenas contadores suportados; swap desconhecida não significa swap usada.

**d** abre detalhes RAM do grupo ou processo: PSS anônima/arquivo/shmem, privada e compartilhada clean/dirty, páginas anônimas, LazyFree e THP. São campos Linux: em outros sistemas n/a. As linhas são vistas sobrepostas e não devem ser todas somadas. A amostra é fixada ao abrir; feche e reabra para atualizar. **Esc** ou **d** fecha os detalhes.

**r** ou **Enter** em um processo abre o mapa de regiões Linux. Em um app, **r** mostra primeiro os PID: cada processo tem espaço virtual próprio. As barras de **d** dividem PSS e RSS separadamente; swap fica fora da RAM residente.

No mapa: **v** alterna RSS/endereços virtuais, **s** ordena, **/** busca arquivo ou endereço 0x…, **f** filtra tipo/estado, **z** ou **Enter** amplia a vizinhança da região selecionada, **r** atualiza e **Esc** limpa filtros/sai do zoom/volta. O mapa segue endereços virtuais, não quadros físicos. Lacunas são excluídas da escala virtual e marcadas com │; regiões menores que um caractere continuam na tabela. Tipo indica a origem, não o conteúdo: um arquivo pode conter páginas CoW privadas; heap/pilha só recebem esse nome quando reconhecidos. Amostras são sob demanda e mostram idade, duração e limites de leitura. Windows: somente intervalos virtuais experimentais; macOS: mapa de regiões indisponível.

Nas regiões, **b** fixa A, **r** coleta B e **c** abre comparação. Nela **v** muda a métrica, **s** a ordem, **f** filtra estado e **Ctrl+B** remove A. **Ctrl+S** salva amostras; **Ctrl+O** abre um arquivo offline. Arquivos contêm metadados e podem incluir caminhos pessoais. Dados ausentes e regiões reorganizadas ficam n/a; o mesmo intervalo não prova a mesma alocação nem vazamento de memória.

**n/a não é zero.** O total de um app é n/a se faltar um único valor. Leituras mostra cobertura PSS/USS. Totais visíveis são somas parciais das leituras disponíveis e não toda a RAM do sistema. Leituras não são atômicas: processos podem mudar durante a amostragem. Outros usuários, ambientes isolados e permissões procfs podem bloqueá-las. Não há elevação automática. HugeTLB é excluído dos contadores RSS/PSS/USS comuns mostrados.

O programa lê metadados, não /proc/PID/mem, cmdline, environment ou conteúdo dos apps.

**g** apps/processos · **Enter** processos do app selecionado · **Esc** voltar aos apps

**s** ordenação · **c** gráfico · **a** todos/primeiros 30 · **m** compacto/completo

**/** busca · **f** filtros · **d** detalhes · **r** regiões · **p** pausa · **?** ajuda · **q** sair

Gráficos: últimas 60 amostras, percentuais na escala 0–100. Espaço vazio indica dado ausente. O intervalo é uma pausa após a medição; o tempo real inclui a varredura.
