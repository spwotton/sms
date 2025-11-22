-- SMS Hub Database Initialization Script
-- This script is automatically run when MySQL container starts for the first time

-- Create contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    relationship ENUM('parent', 'child', 'sibling', 'spouse', 'friend', 'extended_family', 'other') DEFAULT 'other',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_priority (priority),
    INDEX idx_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contact_id INT,
    phone VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    direction ENUM('inbound', 'outbound') NOT NULL,
    status ENUM('pending', 'sent', 'delivered', 'failed') DEFAULT 'pending',
    classification ENUM('stable', 'critical') DEFAULT 'stable',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
    INDEX idx_contact (contact_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    INDEX idx_classification (classification)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert sample contacts (optional)
INSERT INTO contacts (name, phone, priority, relationship) VALUES
    ('John Doe', '+1234567890', 'high', 'parent'),
    ('Jane Smith', '+0987654321', 'critical', 'spouse'),
    ('Bob Johnson', '+1122334455', 'medium', 'friend')
ON DUPLICATE KEY UPDATE id=id;
