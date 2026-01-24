-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 26, 2025 at 07:15 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `file_organizer_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `file_logs`
--

CREATE TABLE `file_logs` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL COMMENT 'ชื่อไฟล์เดิม',
  `extension` varchar(20) NOT NULL COMMENT 'นามสกุลไฟล์',
  `category_name` varchar(50) DEFAULT NULL,
  `source_path` text NOT NULL COMMENT 'ที่อยู่ไฟล์ต้นทาง',
  `destination_path` text NOT NULL COMMENT 'ที่อยู่ไฟล์ปลายทางใหม่',
  `file_size_kb` float DEFAULT NULL COMMENT 'ขนาดไฟล์ (KB)',
  `status` enum('success','failed','duplicate') DEFAULT 'success' COMMENT 'สถานะการย้าย',
  `moved_at` datetime DEFAULT current_timestamp() COMMENT 'วันเวลาที่ทำการย้าย'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `file_logs`
--

INSERT INTO `file_logs` (`id`, `user_id`, `filename`, `extension`, `category_name`, `source_path`, `destination_path`, `file_size_kb`, `status`, `moved_at`) VALUES
(9, 1, 'รูปแกงค์.jpeg', 'jpeg', 'รูปภาพ', 'C:\\Users\\aa249\\Downloads\\one_all\\dfa763e7-a3da-466b-84bb-6f9386043cdb.jpeg', 'C:\\Users\\aa249\\Images\\รูปภาพ\\รูปแกงค์.jpeg', 83.0332, 'success', '2025-12-02 01:19:14'),
(10, 1, 'pack_icon.png', 'png', 'รูปภาพ', 'C:\\Users\\aa249\\Downloads\\one_all\\pack_icon.png', 'C:\\Users\\aa249\\Images\\รูปภาพ\\pack_icon.png', 75.9756, 'success', '2025-12-02 01:19:14'),
(11, 1, 'งานวิจัย knj.docx', 'docx', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\งานวิจัย knj.docx', 'C:\\Users\\aa249\\Documents\\เอกสาร\\งานวิจัย knj.docx', 339.389, 'success', '2025-12-02 19:59:29'),
(12, 1, 'ปัณณวิชญ์ อักษรสาร 1130.docx', 'docx', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ปัณณวิชญ์ อักษรสาร 1130.docx', 'C:\\Users\\aa249\\Documents\\เอกสาร\\ปัณณวิชญ์ อักษรสาร 1130.docx', 692.051, 'success', '2025-12-02 19:59:29'),
(15, 1, 'อะไรนิ.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ความต้องการของผู้สูงอายุด้านการบริการสวัสดิการสังคมเขต อบต.คลองศก แก้ไขแล้ว.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\อะไรนิ.pdf', 987.553, 'success', '2025-12-03 11:37:05'),
(16, 1, 'งานวิจัย knj.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\งานวิจัย knj.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\งานวิจัย knj.pdf', 558.041, 'success', '2025-12-03 11:37:05'),
(17, 1, 'ประเด็นคำถาม.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ประเด็นคำถาม.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\ประเด็นคำถาม.pdf', 304.865, 'success', '2025-12-03 11:37:05'),
(18, 1, 'ปัณณวิชญ์ การคิด.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ปัณณวิชญ์ การคิด.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\ปัณณวิชญ์ การคิด.pdf', 191.7, 'success', '2025-12-03 11:37:05'),
(19, 1, 'ปัณณวิชญ์ อักษรสา 1130.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ปัณณวิชญ์ อักษรสาร 1130.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\ปัณณวิชญ์ อักษรสา 1130.pdf', 612.59, 'success', '2025-12-03 11:37:05'),
(20, 1, 'ปัณณวิชญ์ ชื่อเล่นคอปเตอร์ 6704341001130.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\ปัณณวิชญ์ อักษรสาร ชื่อเล่นคอปเตอร์ 6704341001130.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\ปัณณวิชญ์ ชื่อเล่นคอปเตอร์ 6704341001130.pdf', 42643, 'success', '2025-12-03 11:37:05'),
(21, 1, 'รายชื่อพรีเซนต์.pdf', 'pdf', 'เอกสาร', 'C:\\Users\\aa249\\Downloads\\test\\รายชื่อพรีเซนต์.pdf', 'C:\\Users\\aa249\\Documents\\เอกสาร\\รายชื่อพรีเซนต์.pdf', 45.9492, 'success', '2025-12-03 11:37:05'),
(24, 1, '1.webp', 'webp', 'รูปภาพ', 'C:\\Users\\aa249\\Downloads\\test\\1.webp', 'C:\\Users\\aa249\\Images\\รูปภาพ\\1.webp', 24.4297, 'success', '2025-12-24 01:04:32');

-- --------------------------------------------------------

--
-- Table structure for table `folder_rules`
--

CREATE TABLE `folder_rules` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `category_name` varchar(50) NOT NULL COMMENT 'ชื่อหมวดหมู่ เช่น รูปภาพ, เอกสาร',
  `target_folder_path` varchar(255) NOT NULL COMMENT 'Path ปลายทางที่จะให้ย้ายไป',
  `allowed_extensions` text NOT NULL COMMENT 'นามสกุลไฟล์ (คั่นด้วย comma) เช่น jpg,png,gif',
  `is_active` tinyint(1) DEFAULT 1 COMMENT '1=เปิดใช้งาน, 0=ปิด'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `folder_rules`
--

INSERT INTO `folder_rules` (`id`, `user_id`, `category_name`, `target_folder_path`, `allowed_extensions`, `is_active`) VALUES
(1, 1, 'รูปภาพ', 'C:\\Users\\aa249\\Downloads\\one_all\\Images', '.jpg,.jpeg', 0),
(2, 1, 'รูปภาพ2', 'C:\\Users\\aa249\\Downloads\\Images', '.jpg,.jpeg', 0),
(3, 1, 'รูปภาพ', 'C:\\Users\\aa249\\Downloads\\one_all', '.jpg,.jpeg', 0),
(4, 1, 'รูปภาพ', 'C:\\Users\\aa249\\Images', 'jpg, jpeg, png, gif, bmp, webp', 1),
(5, 1, 'เอกสาร', 'C:\\Users\\aa249\\Documents', 'pdf, doc, docx, txt, xls, xlsx, ppt, pptx', 1),
(6, 1, 'วิดีโอ', 'C:\\Users\\aa249\\Videos', 'mp4, mov, avi, mkv, wmv', 1),
(7, 1, 'เพลง', 'C:\\Users\\aa249\\Music', 'mp3, wav, flac, m4a', 1),
(8, 1, 'บีบอัด', 'C:\\Users\\aa249\\Archives', 'zip, rar, 7z, tar, gz', 1),
(9, 1, 'รูปภาพ2', 'C:\\Users\\aa249\\Images', '.jpg,.jpeg', 0);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `username`, `email`, `password_hash`, `created_at`) VALUES
(1, 'copter', 'admin@mail.com', 'scrypt:32768:8:1$Dx7TX4yQKDQkqxzz$f9e25d1fb1daccb08efcdc484932d9ab4b2139d2ede07209f1b8d7279e2707e943243ebcdd0ea3f6c8b0c1f0fbed738e7b0483b84f4a49afbcc0361a3e199eca', '2025-12-02 00:50:28');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `file_logs`
--
ALTER TABLE `file_logs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_extension` (`extension`),
  ADD KEY `idx_moved_at` (`moved_at`);

--
-- Indexes for table `folder_rules`
--
ALTER TABLE `folder_rules`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`),
  ADD UNIQUE KEY `email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `file_logs`
--
ALTER TABLE `file_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=27;

--
-- AUTO_INCREMENT for table `folder_rules`
--
ALTER TABLE `folder_rules`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
