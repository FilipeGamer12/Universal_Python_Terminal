# UniversalPythonTerminal

**UniversalPythonTerminal** é um terminal gráfico em Python com interface própria em **Tkinter**, conectado a um shell real do sistema operacional. O projeto combina a experiência de um terminal tradicional com recursos extras como **abas**, **histórico persistente**, **aliases personalizados**, **autocompletar**, **visualização interna de arquivos** e **tema configurável**.

Este projeto foi pensado para ser uma alternativa visual e mais amigável a um terminal simples, sem perder a capacidade de executar comandos do sistema.

---

## Principais recursos

- **Interface gráfica com abas** para abrir várias sessões de terminal ao mesmo tempo.
- **Shell real do sistema**: os comandos são enviados ao shell nativo do Windows ou Linux/macOS.
- **Comandos internos próprios** para tarefas comuns, como limpar tela, trocar diretório e abrir arquivos.
- **Histórico persistente** dos últimos comandos digitados.
- **Aliases personalizados** salvos em arquivo JSON.
- **Autocompletar** para comandos internos, aliases e executáveis encontrados no `PATH`.
- **Tema configurável** por arquivo JSON, incluindo cores, destaques e regras de realce.
- **Visualizador interno de arquivos**:
  - imagens com zoom e arrastar;
  - textos com edição e realce de sintaxe;
  - áudio e vídeo com reprodução via VLC;
  - arquivos binários com prévia em hexdump.
- **Detecção e destaque de informações úteis** no terminal, como IPs, caminhos, URLs, datas, horários, e-mails, permissões e estados de serviço.

---

## Tecnologias utilizadas

- **Python 3**
- **Tkinter** para a interface gráfica
- **subprocess / pty** para comunicação com o shell
- **json** para persistência de tema, aliases e histórico
- **Pillow** para visualização avançada de imagens
- **python-vlc** para reprodução de áudio e vídeo

---

## Compatibilidade

O código foi escrito para funcionar em sistemas compatíveis com Python e Tkinter, com suporte diferenciado para:

- **Windows**
- **Linux / Unix-like**

No Windows, o terminal usa o shell definido em `COMSPEC` ou o `cmd.exe` por padrão.
Em sistemas Unix-like, ele usa o shell definido em `SHELL` ou `/bin/bash` como fallback.

---

## Pré-requisitos

Antes de executar o projeto, verifique se você possui:

- **Python 3.10+** recomendado
- **Tkinter** instalado junto ao Python
- **Pillow** para abrir imagens com melhor suporte
- **VLC** instalado no sistema
- **python-vlc** instalado no ambiente Python

### Instalação das dependências opcionais

```bash
pip install pillow python-vlc
```

> O projeto continua funcionando mesmo sem Pillow ou python-vlc, mas alguns recursos ficam limitados.

---

## Como executar

Salve o arquivo principal como `terminal.py` e execute:

```bash
python terminal.py
```

Se estiver usando Linux e o comando `python` não estiver disponível, use:

```bash
python3 terminal.py
```

---

## Estrutura geral do projeto

O arquivo principal concentra toda a aplicação. Ele contém:

- a classe de comunicação com o shell;
- o visualizador interno de arquivos;
- o sistema de abas;
- os comandos internos;
- o carregamento/salvamento do tema;
- a persistência de histórico e aliases.

---

## Como a aplicação funciona

O programa não é apenas uma simulação de terminal. Ele abre uma sessão real do shell e encaminha os comandos digitados para esse processo. Isso significa que você pode usar comandos normais do sistema operacional, além dos comandos internos fornecidos pela própria interface.

A aplicação mantém uma área de saída onde aparecem os resultados dos comandos e uma entrada na parte inferior para digitação. Cada aba possui sua própria sessão de shell.

---

## Comandos internos

Além dos comandos normais do shell, o projeto implementa comandos internos próprios.

### `help` ou `?`
Exibe a ajuda dos comandos internos disponíveis.

### `clear` ou `cls`
Limpa a saída da aba atual.

### `pwd`
Mostra o diretório atual controlado pela interface do terminal.

### `cd <pasta>`
Altera o diretório de trabalho local do emulador.

Exemplo:

```bash
cd C:\Projetos
```

### `ls [pasta]`
Lista arquivos do diretório informado ou do diretório atual.

Exemplo:

```bash
ls
ls Downloads
```

### `alias list`
Lista os aliases salvos.

### `alias add NOME COMANDO`
Cria um alias personalizado.

Exemplo:

```bash
alias add ll ls -la
```

Se o comando usar `%*`, o texto digitado após o alias será inserido nessa posição.

Exemplo:

```bash
alias add greet echo Olá, %*
```

Uso:

```bash
greet mundo
```

### `alias del NOME`
Remove um alias salvo.

Exemplo:

```bash
alias del ll
```

### `view <arquivo>`
Abre um arquivo internamente no visualizador da aplicação.

Exemplo:

```bash
view foto.png
view notas.txt
view video.mp4
```

### `pushd <pasta>`
Altera o diretório local do terminal, de forma parecida com `cd`.

### `popd`
Comando reservado no código atual. Ele existe como comando interno, mas ainda não executa uma pilha de diretórios.

### `exit`
Fecha a aba atual.

---

## Recursos do terminal

### Abas
A interface suporta múltiplas abas. Você pode criar uma nova aba pelo botão `+` ou pelo atalho `Ctrl + T`.

Atalhos principais:

- `Ctrl + T` — nova aba
- `Ctrl + W` — fecha a aba atual
- `Ctrl + Tab` — próxima aba
- `Ctrl + Shift + Tab` — aba anterior

### Histórico
Os comandos digitados são salvos automaticamente em um arquivo JSON no diretório do usuário. O terminal mantém os últimos 20 comandos.

Você pode navegar pelo histórico com:

- `↑` — comando anterior
- `↓` — comando seguinte

### Autocompletar
Ao pressionar `Tab`, o campo de entrada tenta completar:

- comandos internos;
- aliases salvos;
- executáveis encontrados no `PATH`.

### Diretório atual na interface
A parte inferior da aba mostra o diretório atual do terminal. Esse campo pode ser clicado para abrir um seletor de pastas ou editado com duplo clique.

---

## Visualizador interno de arquivos

O comando `view` abre um visualizador próprio para diferentes tipos de arquivo.

### Imagens
Formatos suportados diretamente:

- PNG
- GIF
- PPM
- PGM
- JPG/JPEG
- BMP
- WEBP
- TIF/TIFF

Recursos da visualização de imagens:

- zoom por slider
- zoom com a roda do mouse
- botão para ajustar à tela
- arrastar para navegar em imagens grandes

### Textos
Arquivos de texto podem ser abertos e editados diretamente no visualizador.

O editor inclui:

- salvamento do arquivo;
- recarregamento;
- indentação com `Tab`;
- remoção de indentação com `Shift + Tab`;
- realce básico de sintaxe para vários formatos, como:
  - Python
  - JSON
  - HTML
  - CSS
  - JavaScript
  - XML/YAML
  - C/C++/Java/Go/Rust
  - texto genérico

### Áudio e vídeo
Arquivos de áudio e vídeo podem ser abertos internamente quando `python-vlc` e VLC estiverem instalados.

Formatos reconhecidos incluem, entre outros:

- Áudio: `wav`, `mp3`, `ogg`, `flac`, `aac`, `m4a`, `opus`, `wma`, `aiff`
- Vídeo: `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `m4v`, `mpeg`, `mpg`, `3gp`, `3g2`, `ts`, `m2ts`, `mts`, `f4v`

O player inclui:

- play / pause
- stop
- controle de volume
- barra de progresso
- tempo atual e duração total

### Arquivos binários
Se o arquivo não for texto, imagem ou mídia suportada, a aplicação exibe uma prévia em formato hexdump dos primeiros bytes.

---

## Personalização do tema

O tema da interface é carregado de um arquivo JSON salvo na pasta do usuário:

- `~/.shell_terminal_theme.json`

Esse arquivo controla:

- cores ANSI;
- estilos da saída do terminal;
- tags de destaque;
- regras de realce por expressões regulares.

Se o arquivo não existir, ele é criado automaticamente com o tema padrão.

---

## Arquivos gerados automaticamente

A aplicação salva alguns dados na pasta do usuário:

- `~/.shell_terminal_history.json` — histórico recente de comandos
- `~/.shell_terminal_aliases.json` — aliases personalizados
- `~/.shell_terminal_theme.json` — tema e regras de destaque

---

## Exemplo de uso

```bash
help
pwd
cd Documentos
ls
alias add ll ls -la
ll
view imagem.png
```

---

## Observações importantes

- O projeto depende do shell do sistema, então comandos externos continuam sendo executados pelo ambiente real do usuário.
- O visualizador de imagens tem suporte mais completo com **Pillow** instalado.
- A reprodução de mídia depende de **python-vlc** e do VLC instalado no sistema.
- Alguns comportamentos podem variar entre Windows e Linux devido às diferenças de shell e codificação.
- O comando `popd` está definido como interno, mas no estado atual não altera a pilha de diretórios.
