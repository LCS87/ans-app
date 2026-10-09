"""
Módulo de download de dados da ANS (Demonstrações Contábeis + CADOP).

Baixa todos os arquivos necessários para o pipeline ETL:
1. Demonstração contábeis trimestrais (ZIPs)
2. CADOP - Cadastro de Operadoras de Planos de Saúde (CSV)

Fontes:
- https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/
- https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/

Uso:
    py -m etl.download
    # ou
    py etl/download.py
"""

import asyncio
from pathlib import Path
from typing import List

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# Configurações
ANS_BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA"
DEMONSTRACOES_URL = f"{ANS_BASE_URL}/demonstracoes_contabeis"
CADOP_URL = f"{ANS_BASE_URL}/operadoras_de_plano_de_saude_ativas/Relatorio_cadop.csv"

MIN_ZIP_SIZE_MB = 5  # ZIPs trimestrais são 7-11 MB
MIN_CADOP_SIZE_KB = 100  # CADOP é ~339 KB


class ANSDownloader:
    """Downloader de dados da ANS (demonstrações contábeis + CADOP)."""

    def __init__(self, base_dir: Path = None):
        if base_dir is None:
            # Caminho padrão: etl/data/raw
            base_dir = Path(__file__).parent / "data" / "raw"

        self.base_dir = base_dir
        self.demonstracoes_dir = base_dir / "demonstracoes"
        self.cadop_dir = base_dir / "operadoras_ativas"

        # Criar diretórios
        self.demonstracoes_dir.mkdir(parents=True, exist_ok=True)
        self.cadop_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # DOWNLOAD GENÉRICO
    # ------------------------------------------------------------------
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)
        ),
    )
    async def download_file(self, url: str, dest_path: Path, timeout: int = 300) -> Path:
        """
        Download de arquivo com retry e verificação de integridade.

        Args:
            url: URL do arquivo
            dest_path: Caminho de destino
            timeout: Timeout em segundos

        Returns:
            Path do arquivo baixado
        """
        logger.info(f"⬇️  Iniciando download: {url}")

        # Criar diretório pai se não existir
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Download com streaming
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0

                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Progresso (a cada 1MB)
                        if downloaded_size % (1024 * 1024) < 8192:
                            mb = downloaded_size / (1024 * 1024)
                            if total_size > 0:
                                pct = (downloaded_size / total_size) * 100
                                logger.debug(
                                    f"📊 Progresso: {mb:.2f} MB / {total_size / (1024 * 1024):.2f} MB ({pct:.1f}%)"
                                )
                            else:
                                logger.debug(f"📊 Baixado: {mb:.2f} MB")

        file_size_mb = dest_path.stat().st_size / (1024 * 1024)
        logger.success(f"✅ Download completo: {dest_path.name} ({file_size_mb:.2f} MB)")
        return dest_path

    # ------------------------------------------------------------------
    # DEMONSTRAÇÕES CONTÁBEIS (ZIPs)
    # ------------------------------------------------------------------
    async def download_trimestre(self, ano: int, trimestre: str) -> Path:
        """
        Download de um trimestre específico de demonstrações contábeis.

        Args:
            ano: Ano de referência (ex: 2024)
            trimestre: Trimestre (ex: "1T", "2T", "3T", "4T")

        Returns:
            Path do arquivo ZIP baixado
        """
        filename = f"{trimestre}{ano}.zip"
        url = f"{DEMONSTRACOES_URL}/{ano}/{filename}"
        dest_path = self.demonstracoes_dir / str(ano) / filename

        # Verificar se já existe e está completo
        if dest_path.exists():
            file_size_mb = dest_path.stat().st_size / (1024 * 1024)
            if file_size_mb >= MIN_ZIP_SIZE_MB:
                logger.info(f"⏭️  {filename} já existe ({file_size_mb:.2f} MB), pulando...")
                return dest_path
            else:
                logger.warning(f"⚠️  {filename} incompleto ({file_size_mb:.2f} MB), re-baixando...")
                dest_path.unlink()

        # Download
        path = await self.download_file(url, dest_path)

        # Verificar tamanho mínimo
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb < MIN_ZIP_SIZE_MB:
            path.unlink()
            raise ValueError(
                f"Arquivo muito pequeno: {file_size_mb:.2f} MB (esperado > {MIN_ZIP_SIZE_MB} MB)"
            )

        return path

    async def download_demonstracoes(self, ano: int = 2024) -> List[Path]:
        """
        Download de todos os trimestres de demonstrações contábeis.

        Args:
            ano: Ano de referência (padrão: 2024)

        Returns:
            Lista de paths dos arquivos ZIP baixados
        """
        trimestres = ["1T", "2T", "3T", "4T"]

        logger.info(f"🚀 Iniciando download de demonstrações contábeis de {ano}...")

        files = []
        for tri in trimestres:
            try:
                path = await self.download_trimestre(ano, tri)
                files.append(path)
            except Exception as e:
                logger.error(f"❌ Erro ao baixar {tri}{ano}: {e}")
                # Continua com os próximos trimestres

        logger.success(
            f"✅ Demonstrações de {ano}: {len(files)}/{len(trimestres)} trimestres baixados"
        )
        return files

    # ------------------------------------------------------------------
    # CADOP (Cadastro de Operadoras)
    # ------------------------------------------------------------------
    async def download_cadop(self) -> Path:
        """
        Download do CADOP (Cadastro de Operadoras de Planos de Saúde).

        Returns:
            Path do arquivo CSV baixado
        """
        dest_path = self.cadop_dir / "relatorio_cadop.csv"

        # Verificar se já existe e está completo
        if dest_path.exists():
            file_size_kb = dest_path.stat().st_size / 1024
            if file_size_kb >= MIN_CADOP_SIZE_KB:
                logger.info(f"⏭️  CADOP já existe ({file_size_kb:.1f} KB), pulando...")
                return dest_path
            else:
                logger.warning(f"⚠️  CADOP incompleto ({file_size_kb:.1f} KB), re-baixando...")
                dest_path.unlink()

        logger.info("🚀 Iniciando download do CADOP...")
        path = await self.download_file(CADOP_URL, dest_path)

        # Verificar tamanho mínimo
        file_size_kb = path.stat().st_size / 1024
        if file_size_kb < MIN_CADOP_SIZE_KB:
            path.unlink()
            raise ValueError(
                f"CADOP muito pequeno: {file_size_kb:.1f} KB (esperado > {MIN_CADOP_SIZE_KB} KB)"
            )

        # Validar que é um CSV legível
        import pandas as pd

        try:
            df = pd.read_csv(path, encoding="utf-8", sep=";", on_bad_lines="skip", nrows=5)
            if len(df.columns) < 2:
                raise ValueError("CSV não tem colunas suficientes")
            logger.success(f"✅ CADOP validado: {len(df.columns)} colunas")
        except Exception as e:
            logger.error(f"❌ CADOP inválido: {e}")
            raise

        return path

    # ------------------------------------------------------------------
    # DOWNLOAD COMPLETO
    # ------------------------------------------------------------------
    async def download_all(self, ano: int = 2024) -> dict:
        """
        Download de TODOS os dados necessários para o pipeline.

        Args:
            ano: Ano de referência (padrão: 2024)

        Returns:
            Dict com os paths baixados
        """
        logger.info("=" * 70)
        logger.info("🚀 INICIANDO DOWNLOAD COMPLETO DE DADOS DA ANS")
        logger.info("=" * 70)

        result = {
            "demonstracoes": [],
            "cadop": None,
        }

        # 1. Demonstrações contábeis
        result["demonstracoes"] = await self.download_demonstracoes(ano)

        # 2. CADOP
        try:
            result["cadop"] = await self.download_cadop()
        except Exception as e:
            logger.error(f"❌ Erro ao baixar CADOP: {e}")

        # Resumo
        logger.info("=" * 70)
        logger.info("📊 RESUMO DO DOWNLOAD")
        logger.info("=" * 70)
        for f in result["demonstracoes"]:
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info(f"  ✅ {f.name:<15} | {size_mb:>8.2f} MB")
        if result["cadop"]:
            size_kb = result["cadop"].stat().st_size / 1024
            logger.info(f"  ✅ {'relatorio_cadop.csv':<15} | {size_kb:>8.1f} KB")
        logger.info("=" * 70)

        return result


async def main():
    """Função principal para execução standalone."""
    # Configurar logging em arquivo
    logger.add(
        "etl_download.log",
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    downloader = ANSDownloader()

    try:
        result = await downloader.download_all(2024)

        # Resumo final pro console
        print("\n" + "=" * 60)
        print("📊 RESUMO FINAL DO DOWNLOAD")
        print("=" * 60)
        for f in result["demonstracoes"]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"✅ {f.name:<15} | {size_mb:>8.2f} MB | {f}")
        if result["cadop"]:
            size_kb = result["cadop"].stat().st_size / 1024
            print(f"✅ {'relatorio_cadop.csv':<15} | {size_kb:>8.1f} KB | {result['cadop']}")
        print("=" * 60)

        # Verificar se tudo foi baixado
        ok = len(result["demonstracoes"]) == 4 and result["cadop"] is not None
        if ok:
            print("\n🎉 DOWNLOAD COMPLETO! Todos os arquivos prontos para o ETL.")
        else:
            print("\n⚠️  Alguns arquivos não foram baixados. Verifique os logs.")

    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
