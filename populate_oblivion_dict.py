import os
import json

# ==============================================================================
# Comprehensive The Elder Scrolls IV: Oblivion (オブリビオン) Japanese Localization Dictionary
# Canonical Japanese Xbox 360 / GOTY / PC translations mapped to English equivalents.
# ==============================================================================

BASE_DICTIONARY = {
    # ---------------------------------------------------------
    # Main Menu, HUD & Navigation
    # ---------------------------------------------------------
    "メインメニュー": "Main Menu",
    "メニュー": "Menu",
    "ステータス": "Stats",
    "ステータス画面": "Status Screen",
    "所持品": "Inventory",
    "持ち物": "Inventory",
    "道具": "Items",
    "アイテム": "Items",
    "アイテム一覧": "Item List",
    "装備": "Equip",
    "装備中": "Equipped",
    "装備解除": "Unequip",
    "外す": "Unequip",
    "魔法": "Magic",
    "呪文": "Spells",
    "呪文一覧": "Spell List",
    "有効な効果": "Active Effects",
    "有効な魔法効果": "Active Magic Effects",
    "マップ": "Map",
    "地図": "Map",
    "地域地図": "Local Map",
    "周辺地図": "Local Map",
    "世界地図": "World Map",
    "ファストトラベル": "Fast Travel",
    "マーカー設置": "Place Marker",
    "マーカー削除": "Remove Marker",
    "クエスト": "Quests",
    "クエスト一覧": "Quest List",
    "日誌": "Journal",
    "ジャーナル": "Journal",
    "アクティブクエスト": "Active Quest",
    "現在のクエスト": "Current Quest",
    "完了したクエスト": "Completed Quests",
    "未完了のクエスト": "Active Quests",
    "全てのクエスト": "All Quests",
    "待機": "Wait",
    "睡眠": "Sleep",
    "休憩": "Rest",
    "決定": "Select",
    "キャンセル": "Cancel",
    "戻る": "Back",
    "捨てる": "Drop",
    "取る": "Take",
    "全て取る": "Take All",
    "調べる": "Search",
    "開く": "Open",
    "閉じる": "Close",
    "使用": "Use",
    "使う": "Use",
    "飲む": "Drink",
    "食べる": "Eat",
    "読む": "Read",
    "盗む": "Steal",
    "話す": "Talk",
    "会話": "Talk",
    "説得": "Persuade",
    "取引": "Barter",
    "売買": "Barter",
    "買う": "Buy",
    "売る": "Sell",
    "修理": "Repair",
    "全て修理": "Repair All",
    "訓練": "Train",
    "充填": "Recharge",
    "魂石充填": "Recharge with Soul Gem",
    "レベル": "Level",
    "レベルアップ": "Level Up",
    "オプション": "Options",
    "設定": "Settings",
    "操作設定": "Controls",
    "画面設定": "Video Settings",
    "音量設定": "Audio Settings",
    "ゲームプレイ設定": "Gameplay Settings",
    "セーブ": "Save",
    "ロード": "Load",
    "保存": "Save",
    "読み込み": "Load",
    "クイックセーブ": "Quicksave",
    "クイックロード": "Quickload",
    "ゲームに戻る": "Return to Game",
    "ゲームの終了": "Quit Game",
    "終了": "Quit",
    "はじめから": "New Game",
    "つづきから": "Continue",
    "ニューゲーム": "New Game",
    "コンティニュー": "Continue",

    # ---------------------------------------------------------
    # Core Attributes (8 Attributes)
    # ---------------------------------------------------------
    "腕力": "Strength",
    "知力": "Intelligence",
    "気力": "Willpower",
    "敏捷性": "Agility",
    "速度": "Speed",
    "持久力": "Endurance",
    "魅力": "Personality",
    "運": "Luck",

    # ---------------------------------------------------------
    # Derived Stats & Quantities
    # ---------------------------------------------------------
    "体力": "Health",
    "マジカ": "Magicka",
    "スタミナ": "Fatigue",
    "気力": "Willpower",
    "ファティーグ": "Fatigue",
    "所持重量": "Encumbrance",
    "最大重量": "Max Weight",
    "重量": "Weight",
    "重さ": "Weight",
    "価値": "Value",
    "価格": "Price",
    "ゴールド": "Gold",
    "所持金": "Gold",
    "セプティム": "Septims",
    "防御力": "Armor Rating",
    "防御値": "Armor Rating",
    "アーマー": "Armor",
    "攻撃力": "Damage",
    "ダメージ": "Damage",
    "耐久度": "Condition",
    "耐久性": "Condition",
    "充填量": "Charge",
    "魔力": "Charge",
    "残量": "Uses Remaining",
    "名声": "Fame",
    "悪名": "Infamy",
    "懸賞金": "Bounty",
    "日数": "Days Passed",

    # ---------------------------------------------------------
    # 21 Skills
    # ---------------------------------------------------------
    # Combat
    "刀剣": "Blade",
    "殴打": "Blunt",
    "格闘": "Hand to Hand",
    "防御": "Block",
    "重装": "Heavy Armor",
    "鍛冶": "Armorer",
    "運動": "Athletics",
    # Magic
    "破壊": "Destruction",
    "回復": "Restoration",
    "変性": "Alteration",
    "幻惑": "Illusion",
    "召喚": "Conjuration",
    "神秘": "Mysticism",
    "錬金術": "Alchemy",
    # Stealth
    "隠密": "Sneak",
    "開錠": "Security",
    "軽装": "Light Armor",
    "射手": "Marksman",
    "商才": "Mercantile",
    "話術": "Speechcraft",
    "軽業": "Acrobatics",

    # ---------------------------------------------------------
    # Skill Mastery Levels
    # ---------------------------------------------------------
    "素人": "Novice",
    "見習い": "Apprentice",
    "一人前": "Journeyman",
    "熟練者": "Expert",
    "達人": "Master",

    # ---------------------------------------------------------
    # Races
    # ---------------------------------------------------------
    "アルゴニアン": "Argonian",
    "ブレトン": "Breton",
    "ダークエルフ": "Dark Elf",
    "ダンマー": "Dunmer",
    "ハイエルフ": "High Elf",
    "アルトマー": "Altmer",
    "インペリアル": "Imperial",
    "カジート": "Khajiit",
    "ノルド": "Nord",
    "オーク": "Orc",
    "オルシマー": "Orsimer",
    "レッドガード": "Redguard",
    "ウッドエルフ": "Wood Elf",
    "ボズマー": "Bosmer",
    "ドレモラ": "Dremora",
    "ゴールデン・セイント": "Golden Saint",
    "ダーク・セデューサー": "Dark Seducer",

    # ---------------------------------------------------------
    # Birthsigns
    # ---------------------------------------------------------
    "徒弟": "The Apprentice",
    "淑女": "The Lady",
    "魔術師": "The Mage",
    "盗賊": "The Thief",
    "戦士": "The Warrior",
    "駿馬": "The Steed",
    "影": "The Shadow",
    "儀式": "The Ritual",
    "蛇": "The Serpent",
    "恋人": "The Lover",
    "貴公子": "The Lord",
    "精霊": "The Atronach",
    "塔": "The Tower",

    # ---------------------------------------------------------
    # Equipment Categories & Slots
    # ---------------------------------------------------------
    "武器": "Weapon",
    "防具": "Armor",
    "兜": "Helmet",
    "ヘルメット": "Helmet",
    "キュイラス": "Cuirass",
    "鎧": "Cuirass",
    "胴鎧": "Cuirass",
    "グリーヴ": "Greaves",
    "具足": "Greaves",
    "脛当て": "Greaves",
    "篭手": "Gauntlets",
    "ガントレット": "Gauntlets",
    "手袋": "Gauntlets",
    "ブーツ": "Boots",
    "靴": "Boots",
    "盾": "Shield",
    "シールド": "Shield",
    "大盾": "Tower Shield",
    "指輪": "Ring",
    "リング": "Ring",
    "アミュレット": "Amulet",
    "首飾り": "Necklace",
    "ネックレス": "Necklace",
    "ローブ": "Robe",
    "フード": "Hood",
    "シャツ": "Shirt",
    "ズボン": "Pants",
    "服": "Clothing",

    # ---------------------------------------------------------
    # Base Weapon Types
    # ---------------------------------------------------------
    "ダガー": "Dagger",
    "ショートソード": "Shortsword",
    "短剣": "Shortsword",
    "ロングソード": "Longsword",
    "長剣": "Longsword",
    "クレイモア": "Claymore",
    "大剣": "Claymore",
    "両手剣": "Claymore",
    "刀": "Katana",
    "アカヴィリの刀": "Akaviri Katana",
    "大刀": "Dai-Katana",
    "カトラス": "Cutlass",
    "片手斧": "War Axe",
    "ウォーアックス": "War Axe",
    "バトルアックス": "Battleaxe",
    "両手斧": "Battleaxe",
    "メイス": "Mace",
    "ウォーハンマー": "Warhammer",
    "戦槌": "Warhammer",
    "弓": "Bow",
    "矢": "Arrow",
    "スタッフ": "Staff",
    "杖": "Staff",

    # ---------------------------------------------------------
    # Lockpicking & Containers
    # ---------------------------------------------------------
    "ロックピック": "Lockpick",
    "ピック": "Lockpick",
    "スケルトンキー": "Skeleton Key",
    "修理ハンマー": "Repair Hammer",
    "鍵がかかっている": "Locked",
    "施錠中": "Locked",
    "解錠": "Unlock",
    "鍵が必要": "Requires a Key",
    "難易度: 非常に簡単": "Difficulty: Very Easy",
    "難易度: 簡単": "Difficulty: Easy",
    "難易度: 普通": "Difficulty: Average",
    "難易度: 難しい": "Difficulty: Hard",
    "難易度: 非常に難しい": "Difficulty: Very Hard",
    "非常に簡単": "Very Easy",
    "簡単": "Easy",
    "普通": "Average",
    "難しい": "Hard",
    "非常に難しい": "Very Hard",
    "至難": "Very Hard",
    "開錠に成功しました": "Lock picked.",
    "開錠に失敗しました": "Lockpick broke.",
    "ピックが折れました": "Lockpick broke.",
    "自動開錠": "Auto-Attempt",

    # ---------------------------------------------------------
    # Soul Gems & Welkynd / Varla Stones
    # ---------------------------------------------------------
    "魂石": "Soul Gem",
    "ソウルジェム": "Soul Gem",
    "極小魂石": "Petty Soul Gem",
    "小さな魂石": "Petty Soul Gem",
    "小魂石": "Lesser Soul Gem",
    "小さめの魂石": "Lesser Soul Gem",
    "普通魂石": "Common Soul Gem",
    "普通の魂石": "Common Soul Gem",
    "大魂石": "Greater Soul Gem",
    "大きめの魂石": "Greater Soul Gem",
    "極大魂石": "Grand Soul Gem",
    "黒魂石": "Black Soul Gem",
    "アズラの星": "Azura's Star",
    "ウェルキンド・ストーン": "Welkynd Stone",
    "ヴァーラ・ストーン": "Varla Stone",
    "印石": "Sigil Stone",
    "シジル・ストーン": "Sigil Stone",

    # ---------------------------------------------------------
    # Alchemy Equipment & Potions
    # ---------------------------------------------------------
    "すり鉢とすりこぎ": "Mortar and Pestle",
    "蒸留器": "Retort",
    "レトルト": "Retort",
    "焼鈍器": "Calcinator",
    "カルネーター": "Calcinator",
    "カルシネーター": "Calcinator",
    "アレンビック": "Alembic",
    "蒸留びん": "Alembic",
    "ポーション": "Potion",
    "薬": "Potion",
    "秘薬": "Elixir",
    "毒": "Poison",
    "毒薬": "Poison",
    "体力回復薬": "Potion of Healing",
    "マジカ回復薬": "Potion of Sorcery",
    "スタミナ回復薬": "Potion of Respite",
    "解毒薬": "Potion of Cure Poison",
    "疾病退散薬": "Potion of Cure Disease",
    "解呪薬": "Potion of Dispel",
    "不可視の薬": "Potion of Invisibility",
    "カメレオンの薬": "Potion of Chameleon",
    "暗視の薬": "Potion of Night-Eye",
    "生命探知の薬": "Potion of Detect Life",
    "水中呼吸の薬": "Potion of Water Breathing",
    "羽の薬": "Potion of Feather",
    "軽快の薬": "Potion of Feather",

    # ---------------------------------------------------------
    # Magic Schools, Elements & Spells
    # ---------------------------------------------------------
    "火炎": "Fire Damage",
    "炎": "Fire",
    "火炎ダメージ": "Fire Damage",
    "火炎耐性": "Resist Fire",
    "火炎盾": "Fire Shield",
    "冷気": "Frost Damage",
    "氷結": "Frost",
    "冷気ダメージ": "Frost Damage",
    "冷気耐性": "Resist Frost",
    "冷気盾": "Frost Shield",
    "電撃": "Shock Damage",
    "雷撃": "Shock",
    "電撃ダメージ": "Shock Damage",
    "電撃耐性": "Resist Shock",
    "雷撃盾": "Shock Shield",
    "魔法耐性": "Resist Magic",
    "毒耐性": "Resist Poison",
    "麻痺耐性": "Resist Paralysis",
    "疾病耐性": "Resist Disease",
    "普通武器耐性": "Resist Normal Weapons",
    "麻痺": "Paralyze",
    "沈黙": "Silence",
    "恐怖": "Demoralize",
    "激昂": "Frenzy",
    "錯乱": "Rally",
    "魅了": "Charm",
    "聖域": "Sanctuary",
    "カメレオン": "Chameleon",
    "不可視": "Invisibility",
    "透明化": "Invisibility",
    "暗視": "Night-Eye",
    "生命探知": "Detect Life",
    "光": "Light",
    "水中呼吸": "Water Breathing",
    "水上歩行": "Water Walking",
    "羽": "Feather",
    "軽快": "Feather",
    "負担": "Burden",
    "負荷": "Burden",
    "魂縛": "Soul Trap",
    "武具修復": "Dispel",
    "解呪": "Dispel",
    "念動力": "Telekinesis",
    "体力回復": "Restore Health",
    "マジカ回復": "Restore Magicka",
    "スタミナ回復": "Restore Fatigue",
    "病気治療": "Cure Disease",
    "毒治療": "Cure Poison",
    "体力吸収": "Absorb Health",
    "マジカ吸収": "Absorb Magicka",
    "スタミナ吸収": "Absorb Fatigue",
    "体力低下": "Damage Health",
    "マジカ低下": "Damage Magicka",
    "スタミナ低下": "Damage Fatigue",
    "体力減退": "Drain Health",
    "マジカ減退": "Drain Magicka",
    "スタミナ減退": "Drain Fatigue",
    "体力上昇": "Fortify Health",
    "マジカ上昇": "Fortify Magicka",
    "スタミナ上昇": "Fortify Fatigue",
    "腕力上昇": "Fortify Strength",
    "知力上昇": "Fortify Intelligence",
    "気力上昇": "Fortify Willpower",
    "敏捷性上昇": "Fortify Agility",
    "速度上昇": "Fortify Speed",
    "持久力上昇": "Fortify Endurance",
    "魅力上昇": "Fortify Personality",
    "運上昇": "Fortify Luck",
    "召喚: スケルトン": "Summon Skeleton",
    "召喚: ゾンビ": "Summon Zombie",
    "召喚: スキャンプ": "Summon Scamp",
    "召喚: デイドロス": "Summon Daedroth",
    "召喚: ドレモラ": "Summon Dremora",
    "召喚: クランフィア": "Summon Clannfear",
    "召喚: 炎の精霊": "Summon Flame Atronach",
    "召喚: 氷の精霊": "Summon Frost Atronach",
    "召喚: 雷の精霊": "Summon Storm Atronach",

    # ---------------------------------------------------------
    # Creatures & Enemies
    # ---------------------------------------------------------
    "スケルトン": "Skeleton",
    "ゾンビ": "Zombie",
    "スキャンプ": "Scamp",
    "デイドロス": "Daedroth",
    "ドレモラ": "Dremora",
    "クランフィア": "Clannfear",
    "スパイダー・デイドラ": "Spider Daedra",
    "キヴィライ": "Xivilai",
    "アトロナック": "Atronach",
    "炎の精霊": "Flame Atronach",
    "氷の精霊": "Frost Atronach",
    "雷の精霊": "Storm Atronach",
    "レイス": "Wraith",
    "グール": "Ghoul",
    "リッチ": "Lich",
    "ゴブリン": "Goblin",
    "ラット": "Rat",
    "ネズミ": "Rat",
    "マッドクラブ": "Mudcrab",
    "泥ガニ": "Mudcrab",
    "オオカミ": "Wolf",
    "クマ": "Bear",
    "ライオン": "Mountain Lion",
    "トロール": "Troll",
    "オーガ": "Ogre",
    "ミノタウロス": "Minotaur",
    "ウィスプ": "Will-o-the-Wisp",
    "スローターフィッシュ": "Slaughterfish",
    "山賊": "Bandit",
    "追剥": "Highwayman",
    "魔術師": "Conjurer",
    "死霊術師": "Necromancer",
    "吸血鬼": "Vampire",
    "ヴァンパイア": "Vampire",

    # ---------------------------------------------------------
    # Shivering Isles
    # ---------------------------------------------------------
    "シヴァリング・アイルズ": "Shivering Isles",
    "ニュー・シェオス": "New Sheoth",
    "マニア": "Mania",
    "ディメンシャ": "Dementia",
    "シェオゴラス": "Sheogorath",
    "ハスキンル": "Haskill",
    "ジガルラグ": "Jyggalag",
    "グルミット": "Grummite",
    "バリウオグ": "Baliwog",
    "スカルン": "Scalon",
    "エリトラ": "Elytra",
    "ナール": "Gnarl",
    "琥珀": "Amber",
    "狂気の鉱石": "Madness Ore",
    "琥珀のインゴット": "Amber Ingot",
    "狂気": "Madness",
    "ジガルラグの剣": "Sword of Jyggalag",
    "苦痛の宮殿": "Palace of Sheogorath",

    # ---------------------------------------------------------
    # Major Cities & Locations
    # ---------------------------------------------------------
    "シロディール": "Cyrodiil",
    "帝都": "Imperial City",
    "商業地区": "Market District",
    "アリーナ地区": "Arena District",
    "波止場地区": "Waterfront District",
    "エルフ・ガーデン地区": "Elven Gardens District",
    "神殿地区": "Temple District",
    "タロス広場地区": "Talos Plaza District",
    "グリーン・エンペラー通り": "Green Emperor Way",
    "宮殿": "Imperial Palace",
    "アンヴィル": "Anvil",
    "ブラヴィル": "Bravil",
    "ブルマ": "Bruma",
    "シェイディンハル": "Cheydinhal",
    "コロール": "Chorrol",
    "レヤウィン": "Leyawiin",
    "スキングラード": "Skingrad",
    "クヴァッチ": "Kvatch",
    "オブリビオンの門": "Oblivion Gate",

    # ---------------------------------------------------------
    # Guilds & Factions
    # ---------------------------------------------------------
    "戦士ギルド": "Fighters Guild",
    "魔術師ギルド": "Mages Guild",
    "盗賊ギルド": "Thieves Guild",
    "闇の一党": "Dark Brotherhood",
    "ブレイド": "The Blades",
    "帝都軍": "Imperial Legion",
    "アリーナ": "Arena",
    "闘技場": "Arena",
    "闘技場の挑戦者": "Pit Dog",
    "剣闘士": "Gladiator",
    "英雄": "Grand Champion",
    "チャンピオン": "Champion",
    "グレイ・フォックス": "The Gray Fox",
    "九大神": "Nine Divines",
    "九大神の騎士": "Knights of the Nine",

    # ---------------------------------------------------------
    # Canonical Dialogue & Persuasion Mini-Game
    # ---------------------------------------------------------
    "噂話": "Rumors",
    "うわさ": "Rumors",
    "お世辞": "Admire",
    "賞賛": "Admire",
    "自慢": "Boast",
    "冗談": "Joke",
    "脅迫": "Coerce",
    "好感度": "Disposition",
    "さようなら": "Goodbye",
    "何か用か？": "What do you want?",
    "話を聞こう": "I'm listening.",

    # ---------------------------------------------------------
    # In-Game Prompts, Guards, Crime & System Notifications
    # ---------------------------------------------------------
    "敵が近くにいるため待機できません": "You cannot wait with enemies nearby.",
    "敵が近くにいるため待機できません。": "You cannot wait with enemies nearby.",
    "敵が近くにいるため睡眠できません": "You cannot sleep with enemies nearby.",
    "敵が近くにいるため睡眠できません。": "You cannot sleep with enemies nearby.",
    "戦闘中はファストトラベルできません": "You cannot fast travel during combat.",
    "戦闘中はファストトラベルできません。": "You cannot fast travel during combat.",
    "重すぎて移動できません": "You are over-encumbered.",
    "重すぎて移動できません。": "You are over-encumbered.",
    "重量オーバー": "Over-encumbered",
    "所持品がいっぱいです": "Inventory is full.",
    "レベルアップ可能です": "You should rest and meditate on what you have learned.",
    "クエスト更新": "Quest Updated",
    "クエスト完了": "Quest Completed",
    "持ち物を捨てました": "Item dropped.",
    "所持品に追加されました": "Added to inventory.",
    "武器が破損しました": "Weapon broken.",
    "防具が破損しました": "Armor broken.",
    "修理に成功しました": "Item repaired.",
    "修理ハンマーが壊れました": "Repair hammer broke.",
    "充填が切れました": "Insufficient charge.",
    "不法侵入": "Trespassing",
    "盗み": "Stealing",
    "殺人": "Murder",
    "衛兵": "Guard",
    "止まれ！": "Stop right there, criminal scum!",
    "法を犯したな！": "You have committed crimes against Cyrodiil!",
    "罰金を払う": "Pay the fine",
    "刑務所に行く": "Go to jail",
    "抵抗する": "Resist arrest",
}

# ==============================================================================
# Combinatorial Generation: Materials x Equipment Types
# Creates canonical names for all Oblivion weapons and armors.
# ==============================================================================

MATERIALS = [
    ("錆びた", "Rusted"),
    ("鉄", "Iron"),
    ("鋼鉄", "Steel"),
    ("銀", "Silver"),
    ("ドワーフ", "Dwarven"),
    ("オーク", "Orcish"),
    ("エルフ", "Elven"),
    ("グラス", "Glass"),
    ("黒檀", "Ebony"),
    ("デイドラ", "Daedric"),
    ("毛皮", "Fur"),
    ("革", "Leather"),
    ("鎖帷子", "Chainmail"),
    ("スケール", "Scale"),
    ("ミスリル", "Mithril"),
    ("琥珀", "Amber"),
    ("狂気", "Madness"),
]

WEAPONS = [
    ("ダガー", "Dagger"),
    ("ショートソード", "Shortsword"),
    ("ロングソード", "Longsword"),
    ("クレイモア", "Claymore"),
    ("片手斧", "War Axe"),
    ("バトルアックス", "Battleaxe"),
    ("両手斧", "Battleaxe"),
    ("メイス", "Mace"),
    ("ウォーハンマー", "Warhammer"),
    ("戦槌", "Warhammer"),
    ("弓", "Bow"),
    ("矢", "Arrow"),
]

ARMORS = [
    ("キュイラス", "Cuirass"),
    ("鎧", "Cuirass"),
    ("兜", "Helmet"),
    ("ヘルメット", "Helmet"),
    ("グリーヴ", "Greaves"),
    ("具足", "Greaves"),
    ("脛当て", "Greaves"),
    ("篭手", "Gauntlets"),
    ("ガントレット", "Gauntlets"),
    ("ブーツ", "Boots"),
    ("靴", "Boots"),
    ("盾", "Shield"),
    ("シールド", "Shield"),
    ("大盾", "Tower Shield"),
]

def generate_oblivion_dictionary():
    dict_all = dict(BASE_DICTIONARY)

    # 1. Combinations of Materials x Weapons
    for m_ja, m_en in MATERIALS:
        for w_ja, w_en in WEAPONS:
            # "鉄のロングソード" -> "Iron Longsword"
            dict_all[f"{m_ja}の{w_ja}"] = f"{m_en} {w_en}"
            # "鉄ロングソード" -> "Iron Longsword"
            dict_all[f"{m_ja}{w_ja}"] = f"{m_en} {w_en}"

    # 2. Combinations of Materials x Armors
    for m_ja, m_en in MATERIALS:
        for a_ja, a_en in ARMORS:
            # "鋼鉄のキュイラス" -> "Steel Cuirass"
            dict_all[f"{m_ja}の{a_ja}"] = f"{m_en} {a_en}"
            # "鋼鉄キュイラス" -> "Steel Cuirass"
            dict_all[f"{m_ja}{a_ja}"] = f"{m_en} {a_en}"

    # 3. Potion Potency Tiers
    potion_effects = [
        ("体力回復薬", "Potion of Health"),
        ("マジカ回復薬", "Potion of Magicka"),
        ("スタミナ回復薬", "Potion of Fatigue"),
        ("体力回復", "Restore Health"),
        ("マジカ回復", "Restore Magicka"),
        ("スタミナ回復", "Restore Fatigue"),
        ("解毒薬", "Cure Poison"),
        ("疾病退散薬", "Cure Disease"),
        ("羽の薬", "Potion of Feather"),
        ("不可視の薬", "Potion of Invisibility"),
    ]
    tiers = [
        ("（極小）", "(Petty)"),
        ("（小）", "(Lesser)"),
        ("（中）", "(Common)"),
        ("（大）", "(Greater)"),
        ("（極大）", "(Grand)"),
        ("（弱）", "(Weak)"),
        ("（並）", "(Standard)"),
        ("（強）", "(Strong)"),
        ("(極小)", "(Petty)"),
        ("(小)", "(Lesser)"),
        ("(中)", "(Common)"),
        ("(大)", "(Greater)"),
        ("(極大)", "(Grand)"),
        ("(弱)", "(Weak)"),
        ("(並)", "(Standard)"),
        ("(強)", "(Strong)"),
    ]
    for p_ja, p_en in potion_effects:
        for t_ja, t_en in tiers:
            dict_all[f"{p_ja}{t_ja}"] = f"{p_en} {t_en}"

    # 4. Common Oblivion Menu Suffixes & Compounds
    menu_stems = [
        ("ステータス", "Status"),
        ("所持品", "Inventory"),
        ("魔法", "Magic"),
        ("地図", "Map"),
        ("クエスト", "Quest"),
        ("装備", "Equipment"),
    ]
    suffixes = [
        ("画面", "Screen"),
        ("一覧", "List"),
        ("変更", "Change"),
        ("確認", "Check"),
        ("情報", "Info"),
    ]
    for m_ja, m_en in menu_stems:
        for s_ja, s_en in suffixes:
            dict_all[f"{m_ja}{s_ja}"] = f"{m_en} {s_en}"

    return dict_all

def populate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, "translations.json")
    root_path = os.path.join(os.path.dirname(base_dir), "translations.json")

    full_dict = generate_oblivion_dictionary()
    print(f"[Oblivion Dict] Generated {len(full_dict)} canonical Oblivion terms.")

    for path in [target_path, root_path]:
        existing = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception as e:
                print(f"[Oblivion Dict] Error reading {path}: {e}")

        before_cnt = len(existing)
        # Merge Oblivion terms with priority
        for k, v in full_dict.items():
            existing[k] = v

        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        after_cnt = len(existing)
        print(f"[Oblivion Dict] Updated {path}: {before_cnt} -> {after_cnt} (+{after_cnt - before_cnt} entries)")

if __name__ == "__main__":
    populate()
