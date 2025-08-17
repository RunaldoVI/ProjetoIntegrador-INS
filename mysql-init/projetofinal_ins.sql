-- Bootstrap: BD + utilizador + permissões
CREATE DATABASE IF NOT EXISTS `projetofinal_ins`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

CREATE USER IF NOT EXISTS 'user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON `projetofinal_ins`.* TO 'user'@'%';
FLUSH PRIVILEGES;

USE `projetofinal_ins`;

-- (opcional) settings do dump
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";
SET NAMES utf8mb4;

-- Estrutura da tabela `perguntas`
CREATE TABLE IF NOT EXISTS `perguntas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `texto` text NOT NULL,
  `identificador-pergunta` VARCHAR(32) NULL,
  `identificador-semantico` int NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Estrutura da tabela `respostas`
CREATE TABLE IF NOT EXISTS `respostas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `texto` text NOT NULL,
  `identificador-pergunta` VARCHAR(32) NULL,
  `identificador-semantico` int NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Estrutura da tabela `utilizador`
CREATE TABLE IF NOT EXISTS `utilizador` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `funcao` varchar(50) NOT NULL,
  `instituicao` varchar(100) NOT NULL,
  `avatar` varchar(255) NOT NULL DEFAULT 'default.png',
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Estrutura da tabela `historico_pdfs`
CREATE TABLE IF NOT EXISTS `historico_pdfs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `utilizador_id` int(11) NOT NULL,
  `nome_pdf` varchar(255) NOT NULL,
  `data_upload` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `utilizador_id` (`utilizador_id`),
  CONSTRAINT `historico_pdfs_ibfk_1` FOREIGN KEY (`utilizador_id`) REFERENCES `utilizador` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Estrutura da tabela `pergunta_resposta`
CREATE TABLE IF NOT EXISTS `pergunta_resposta` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `pergunta_id` int(11) NOT NULL,
  `resposta_id` int(11) NOT NULL,
  `texto_pergunta` TEXT,
  `texto_resposta` TEXT,
  PRIMARY KEY (`id`),
  KEY `pergunta_id` (`pergunta_id`),
  KEY `resposta_id` (`resposta_id`),
  CONSTRAINT `pergunta_resposta_ibfk_1` FOREIGN KEY (`pergunta_id`) REFERENCES `perguntas` (`id`) ON DELETE CASCADE,
  CONSTRAINT `pergunta_resposta_ibfk_2` FOREIGN KEY (`resposta_id`) REFERENCES `respostas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
