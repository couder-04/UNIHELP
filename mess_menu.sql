-- mess_menu.sql
-- Hostel mess menus. Reads always hit `temporary`. Writes go to
-- `temporary` (faculty/admin) or `permanent` (admin only).
--
-- Run inside the dedicated `mess_menu` database.

BEGIN;

CREATE TABLE IF NOT EXISTS temporary (
    hostel TEXT NOT NULL,
    day TEXT NOT NULL,
    breakfast TEXT,
    lunch TEXT,
    snacks TEXT,
    dinner TEXT,
    PRIMARY KEY (hostel, day)
);

CREATE TABLE IF NOT EXISTS permanent (
    hostel TEXT NOT NULL,
    day TEXT NOT NULL,
    breakfast TEXT,
    lunch TEXT,
    snacks TEXT,
    dinner TEXT,
    PRIMARY KEY (hostel, day)
);

CREATE INDEX IF NOT EXISTS idx_temporary_hostel_day
    ON temporary (LOWER(hostel), LOWER(day));

CREATE INDEX IF NOT EXISTS idx_permanent_hostel_day
    ON permanent (LOWER(hostel), LOWER(day));

-- Sample weekly menus for the hostels the agent examples use.
INSERT INTO temporary (hostel, day, breakfast, lunch, snacks, dinner)
SELECT hostel, day, breakfast, lunch, snacks, dinner
FROM (
    VALUES
        ('Kalam', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Kalam', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Kalam', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Kalam', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Kalam', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Kalam', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Kalam', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('Aryabhatta', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Aryabhatta', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Aryabhatta', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Aryabhatta', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Aryabhatta', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Aryabhatta', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Aryabhatta', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('CV Raman', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('CV Raman', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('CV Raman', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('CV Raman', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('CV Raman', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('CV Raman', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('CV Raman', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice'),

        ('Asima', 'Monday',    'Poha, banana, tea',           'Rice, dal, mixed veg, roti',     'Samosa, tea',     'Roti, dal, paneer, rice'),
        ('Asima', 'Tuesday',   'Idli, sambar, coffee',        'Jeera rice, chole, salad',       'Bhel, lemonade',  'Roti, palak paneer, rice'),
        ('Asima', 'Wednesday', 'Paratha, curd, tea',          'Rice, sambar, cabbage, roti',    'Pakora, tea',     'Roti, egg curry, rice'),
        ('Asima', 'Thursday',  'Upma, fruit, tea',            'Rice, rajma, beans, roti',       'Sandwich, juice', 'Roti, chicken curry, rice'),
        ('Asima', 'Friday',    'Bread omelette, tea',         'Fried rice, dal tadka, roti',    'Vada, coffee',    'Roti, fish curry, rice'),
        ('Asima', 'Saturday',  'Aloo paratha, pickle, tea',   'Rice, kadhi, aloo gobi, roti',   'Noodles, tea',    'Roti, mix veg, rice'),
        ('Asima', 'Sunday',    'Chole bhature, tea',          'Veg biryani, raita, papad',      'Cake, coffee',    'Roti, malai kofta, rice')
) AS seed(hostel, day, breakfast, lunch, snacks, dinner)
ON CONFLICT (hostel, day) DO NOTHING;

INSERT INTO permanent (hostel, day, breakfast, lunch, snacks, dinner)
SELECT hostel, day, breakfast, lunch, snacks, dinner
FROM temporary
ON CONFLICT (hostel, day) DO NOTHING;

COMMIT;
