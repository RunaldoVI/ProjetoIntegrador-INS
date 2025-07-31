-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 30-Jul-2025 às 03:14
-- Versão do servidor: 10.4.32-MariaDB
-- versão do PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `projetofinal_ins`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `identificadores`
--

CREATE TABLE `identificadores` (
  `id` int(11) NOT NULL,
  `codigo` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `perguntas`
--

CREATE TABLE `perguntas` (
  `id` int(11) NOT NULL,
  `texto` text NOT NULL,
  `identificador_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `pergunta_resposta`
--

CREATE TABLE `pergunta_resposta` (
  `pergunta_id` int(11) NOT NULL,
  `resposta_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `respostas`
--

CREATE TABLE `respostas` (
  `id` int(11) NOT NULL,
  `texto` text NOT NULL,
  `identificador_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `Utilizador`
--

CREATE TABLE `utilizador` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `funcao` varchar(50) NOT NULL,
  `instituicao` varchar(100) NOT NULL,
  `avatar` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Estrutura da tabela `historico_pdfs`
--

CREATE TABLE `historico_pdfs` (
  `id` int(11) NOT NULL,
  `utilizador_id` int(11) NOT NULL,
  `nome_pdf` varchar(255) NOT NULL,
  `data_upload` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- --------------------------------------------------------

--
-- Índices para tabela `Utilizador`
--

ALTER TABLE `utilizador`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  MODIFY avatar VARCHAR(255) NOT NULL DEFAULT 'default.png';


--
-- Índices para tabela `identificadores`
--
ALTER TABLE `identificadores`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `codigo` (`codigo`);

--
-- Índices para tabela `perguntas`
--
ALTER TABLE `perguntas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `identificador_id` (`identificador_id`);

--
-- Índices para tabela `pergunta_resposta`
--
ALTER TABLE `pergunta_resposta`
  ADD PRIMARY KEY (`pergunta_id`,`resposta_id`),
  ADD KEY `resposta_id` (`resposta_id`);

--
-- Índices para tabela `historico_pdfs`
--
ALTER TABLE `historico_pdfs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `utilizador_id` (`utilizador_id`);


--
-- Índices para tabela `respostas`
--
ALTER TABLE `respostas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `identificador_id` (`identificador_id`);

--
-- AUTO_INCREMENT de tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `utilizador`
--
ALTER TABLE `utilizador`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `identificadores`
--
ALTER TABLE `identificadores`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `perguntas`
--
ALTER TABLE `perguntas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `respostas`
--
ALTER TABLE `respostas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT da tabela `historico_pdfs`
--
ALTER TABLE `historico_pdfs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restrições para despejos de tabelas
--

--
-- Limitadores para a tabela `perguntas`
--
ALTER TABLE `perguntas`
  ADD CONSTRAINT `perguntas_ibfk_1` FOREIGN KEY (`identificador_id`) REFERENCES `identificadores` (`id`);

--
-- Limitadores para a tabela `pergunta_resposta`
--
ALTER TABLE `pergunta_resposta`
  ADD CONSTRAINT `pergunta_resposta_ibfk_1` FOREIGN KEY (`pergunta_id`) REFERENCES `perguntas` (`id`),
  ADD CONSTRAINT `pergunta_resposta_ibfk_2` FOREIGN KEY (`resposta_id`) REFERENCES `respostas` (`id`);

--
-- Limitadores para a tabela `respostas`
--
ALTER TABLE `respostas`
  ADD CONSTRAINT `respostas_ibfk_1` FOREIGN KEY (`identificador_id`) REFERENCES `identificadores` (`id`);
COMMIT;

--
-- Restrições para a tabela `historico_pdfs`
--
ALTER TABLE `historico_pdfs`
  ADD CONSTRAINT `historico_pdfs_ibfk_1` FOREIGN KEY (`utilizador_id`) REFERENCES `utilizador` (`id`) ON DELETE CASCADE;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
