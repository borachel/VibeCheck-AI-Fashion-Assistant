import sqlite3

def setup_database():
    conn = sqlite3.connect('fashion_store.db')
    c = conn.cursor()
    
    # Tạo bảng mới
    c.execute('''CREATE TABLE products 
                 (id INTEGER PRIMARY KEY, 
                  name TEXT, 
                  gender TEXT,   -- Nam, Nữ
                  style TEXT,    -- Minimalism, Y2K, Sporty, Elegant, Vintage
                  occasion TEXT, -- Đi tiệc, Đi làm, Đi chơi, Đi hẹn hò
                  body_shape TEXT, -- Hourglass, Triangle, Inverted Triangle, Rectangle, Ovals
                  price TEXT,
                  image_url TEXT)''')
    
    # Thêm dữ liệu mẫu (Bạn hãy thay link_anh_that bằng link ảnh sản phẩm của bạn)
    sample_data = [
# --- NHÓM NỮ (20 Items) ---
    # ========================== NHÓM NỮ (16 Items) ==========================
    # Đi làm
    	(1, 'Sơ mi trắng lụa', 'Nữ', 'Elegant', 'Đi làm', 'All', '550.000đ', 'https://i.postimg.cc/1zxD1J8k/1.png'),
    	(2, 'Blazer công sở', 'Nữ', 'Elegant', 'Đi làm', 'All', '950.000đ', 'https://i.postimg.cc/NGVnrvSx/2.png'),
    	(3, 'Sơ mi chiết eo', 'Nữ', 'Elegant', 'Đi làm', 'Hourglass', '480.000đ', 'https://i.postimg.cc/8z3Z5B61/3.jpg'),
    	(4, 'Sơ mi cổ V dáng suông', 'Nữ', 'Minimalism', 'Đi làm', 'Ovals', '350.000đ', 'https://i.postimg.cc/5jdr6BG4/4.jpg'),

    # Đi chơi
    	(5, 'Áo thun Baby Tee', 'Nữ', 'Y2K', 'Đi chơi', 'All', '150.000đ', 'https://i.postimg.cc/g2RZVvTs/5.jpg'),
    	(6, 'Cardigan mỏng', 'Nữ', 'Vintage', 'Đi chơi', 'All', '450.000đ', 'https://i.postimg.cc/pTnrvxMZ/6.jpg'),
    	(7, 'Áo trễ vai', 'Nữ', 'Y2K', 'Đi chơi', 'Triangle', '280.000đ', 'https://i.postimg.cc/DfBHhGB8/7.jpg'),
    	(8, 'Croptop ôm sát', 'Nữ', 'Sporty', 'Đi chơi', 'Rectangle', '250.000đ', 'https://i.postimg.cc/pdWKPmsJ/8.jpg'),

    # Đi tiệc
    	(9, 'Váy Satin quai mảnh', 'Nữ', 'Elegant', 'Đi tiệc', 'All', '650.000đ', 'https://i.postimg.cc/9QbrYC2R/9.jpg'),
    	(10, 'Váy lụa bất đối xứng', 'Nữ', 'Elegant', 'Đi tiệc', 'All', '850.000đ', 'https://i.postimg.cc/6QCbmjHw/10.jpg'),
    	(11, 'Váy suông Shift Dress', 'Nữ', 'Minimalism', 'Đi tiệc', 'Ovals', '750.000đ', 'https://i.postimg.cc/L83NkYhs/11.jpg'),
    	(12, 'Áo Corset phối ren', 'Nữ', 'Vintage', 'Đi tiệc', 'Inverted Triangle', '550.000đ', 'https://i.postimg.cc/cL5y7bv7/12.jpg'),

    # Đi hẹn hò
    	(13, 'Áo chấm bi thắt nơ', 'Nữ', 'Elegant', 'Đi hẹn hò', 'All', '390.000đ', 'https://i.postimg.cc/pdNktf7B/13.jpg'),
    	(14, 'Áo crop hoa nhí', 'Nữ', 'Vintage', 'Đi hẹn hò', 'All', '350.000đ', 'https://i.postimg.cc/DzJZ1syM/14.jpg'),
    	(15, 'Áo ren xếp ly', 'Nữ', 'Vintage', 'Đi hẹn hò', 'Ovals', '420.000đ', 'https://i.postimg.cc/vBYNp7g7/15.jpg'),
    	(16, 'Áo tay bồng', 'Nữ', 'Elegant', 'Đi hẹn hò', 'Triangle', '380.000đ', 'https://i.postimg.cc/qMwXFfXT/16.jpg'),

    # ========================== NHÓM NAM (16 Items) ==========================
    # Đi làm
    	(17, 'Sơ mi trắng Oxford', 'Nam', 'Minimalism', 'Đi làm', 'All', '450.000đ', 'https://i.postimg.cc/L5X66ZwF/17.jpg'),
    	(18, 'Áo Polo chỉn chu', 'Nam', 'Minimalism', 'Đi làm', 'All', '350.000đ', 'https://i.postimg.cc/hG1dXTCH/18.jpg'),
    	(19, 'Sơ mi Henley kẻ caro', 'Nam', 'Elegant', 'Đi làm', 'Inverted Triangle', '480.000đ', 'https://i.postimg.cc/2j7rgTqy/19.jpg'),
    	(20, 'Sweater cổ khóa', 'Nam', 'Elegant', 'Đi làm', 'Rectangle', '550.000đ', 'https://i.postimg.cc/NFMJJg9x/20.jpg'),

    # Đi chơi
    	(21, 'Thun Oversized Cotton', 'Nam', 'Sporty', 'Đi chơi', 'All', '250.000đ', 'https://i.postimg.cc/gcQKH3ph/21.jpg'),
    	(22, 'Áo khoác gió nhẹ', 'Nam', 'Sporty', 'Đi chơi', 'All', '550.000đ', 'https://i.postimg.cc/K8qjtDXB/22.jpg'),
    	(23, 'Coach Jacket', 'Nam', 'Vintage', 'Đi chơi', 'Ovals', '650.000đ', 'https://i.postimg.cc/13nhYGnw/23.jpg'),
    	(24, 'Sơ mi Cuba họa tiết', 'Nam', 'Vintage', 'Đi chơi', 'Triangle', '350.000đ', 'https://i.postimg.cc/ry0HTVFr/24.jpg'),

    # Đi tiệc
    	(25, 'Vest/Blazer đen', 'Nam', 'Elegant', 'Đi tiệc', 'All', '1.500.000đ', 'https://i.postimg.cc/ZRhWqKzk/25.jpg'),
    	(26, 'Sơ mi lụa bóng', 'Nam', 'Elegant', 'Đi tiệc', 'All', '650.000đ', 'https://i.postimg.cc/tCfCTCFB/26.jpg'),
    	(27, 'Velvet Blazer', 'Nam', 'Elegant', 'Đi tiệc', 'Ovals', '1.800.000đ', 'https://i.postimg.cc/vmvsWQ6Z/27.jpg'),
    	(28, 'Double Breasted Blazer', 'Nam', 'Elegant', 'Đi tiệc', 'Triangle', '2.200.000đ', 'https://i.postimg.cc/jjRVqG3p/28.jpg'),

    # Đi hẹn hò
    	(29, 'Sơ mi vải lanh cổ tàu', 'Nam', 'Minimalism', 'Đi hẹn hò', 'All', '420.000đ', 'https://i.postimg.cc/13fBGMnD/29.jpg'),
    	(30, 'Áo thun Henley', 'Nam', 'Minimalism', 'Đi hẹn hò', 'All', '290.000đ', 'https://i.postimg.cc/WzdzWDM3/30.jpg'),
    	(31, 'Áo thun form-fitting', 'Nam', 'Sporty', 'Đi hẹn hò', 'Triangle', '750.000đ', 'https://i.postimg.cc/J7sjdt7k/31.jpg'),
    	(32, 'Cardigan dệt kim', 'Nam', 'Vintage', 'Đi hẹn hò', 'Ovals', '450.000đ', 'https://i.postimg.cc/RVRC7Lr7/32.jpg')
    ]
    
    c.executemany('INSERT INTO products VALUES (?,?,?,?,?,?,?,?)', sample_data)
    conn.commit()
    conn.close()
    print("Database updated successfully!")

if __name__ == "__main__":
    setup_database()