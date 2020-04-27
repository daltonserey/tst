# tst [![Português](images/BR.png)](README.pt-BR.md) [![English](images/US.png)](README.md)

O tst é um conjunto de ferramentas de linha de comando que
permite criar e responder exercícios de programação que podem ser
testados e verificados automaticamente. Foi inicialmente criado
para facilitar a vido do professor, automatizando o processo de
testes das respostas de vários alunos para um mesmo exercício.
Com o tempo também se mostrou útil para os estudantes, permitindo
que eles recebam e executem parte dos testes automáticos
planejados e que possam criar seus próprios testes com
facilidade.

Grosso modo, o tst suporta dois tipos de testes: testes de
entrada e saída e scripts de teste. Testes de entrada e
saída permitem executar o programa do estudante, fornecer-lhe uma
dada entrada, coletar a saída e compará-la a uma saída esperada.
Scripts de teste são scripts (programas), tipicamente escritos em
Python, que devem ler e processar o programa resposta do
estudante e produzir uma saída em um formato esperado, de acordo
com o protocolo tst. Estas duas formas de testes permitem que uma
significativa variedade de testes e verificações possam ser
executadas sobre as respostas dos alunos. Além disso, torna
o processo agnóstico em relação à linguagem alvo. Tipicamente,
contudo, o tst tem sido usado para exercícios em Python e Node
(também já o usamos com Java).

## Licença

Este software é licensiado sob os termos da licença AGPL 3.0.
Por favor, leia o arquivo LICENSE.


## Instalação

Os scripts tst são escritos em Python e estão disponíveis [no
repositório Pypi](http://pypi.org/project/tst). A partir da
versão 0.10, pretendo dar suporte apenas a Python 3. Os scripts
foram feitos para serem instalados no espaço do usuário (isso
facilita a atualização e mantém a independência do restante do
sistema). Para instalar use o comando `pip3`, como indicado
abaixo.

```
pip3 install --user tst
```

É bastante provável que uma versão menos estável, mas com novas
funcionalidades e/ou com menos alguns (e talvez mais alguns
outros) esteja sendo testada (uma versao _pre-release_). Se você
deseja (ou foi instruído a) instalar a versão _pre-release_, use
o comando abaixo.

> Importante. Observe que `pip3` instala os executáveis dos
> pacotes no diretório `~/.local/bin` (no Linux) e em
> `~/Library/Python/VERSAO/bin/` (no Mac). Para que o comando `tst`
> fique disponível, você precisa garantir que esse diretório
> esteja no PATH do seu ambiente.


```
pip3 install --user --pre tst
```

Se você deseja ou precisa desinstalar o tst, use o comando
abaixo.

```
pip3 uninstall tst
```
