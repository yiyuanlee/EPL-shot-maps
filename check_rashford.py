import os

vault = r'C:\Users\23150\OneDrive\文档\Obsidian_1\渊神智库'
invest_dir = os.path.join(vault, '投资')

# 1. Create 投资/概览.md (copy from wiki version)
overview = """# 投资概览

> 李奕渊的个人投资知识库

## 持仓（2026-04-30 更新）

### 盈利中
- GOOGL 7股 | 市值 $2,449.58 | +18.2%
- MSFT 4股 | 市值 $1,697.84 | +4.8%
- NVDA 7股 | 市值 $1,464.75 | +11.2%

### 亏损中
- PG 5股 | 市值 $732.30 | -12.5%
- BABA 5股 | 市值 $652.15 | -23.0%
- CRCL 6股 | 市值 $573.36 | -27.8%
- ETH 约0.26个 | 市值 $540.32 | -45.9%
- SOL 约3个 | 市值 $236.73 | -69.2%
- SHIBxM 约0.68个 | 市值 $4.11 | -76.9%

**总市值：$8,351.14 USD**

## 投资策略
- 美股为主（科技股为主）
- 加密货币为辅（ETH, SOL, SHIBxM）

## 来源
- Notion Portfolio Records
- CNBC 实时行情

## 相关页面
- [[持仓详情-2026-04-30]]
"""

with open(os.path.join(invest_dir, '概览.md'), 'w', encoding='utf-8') as f:
    f.write(overview)
print("Created: 投资/概览.md")

# 2. Create detailed 投资/持仓.md
holdings = """# 持仓详情

> 最后更新：2026-04-30 | 数据来源：Notion Portfolio Records

## 股票

| 股票 | 股数 | 成本价 | 现价 | 市值 | 盈亏 | 盈亏% |
|------|------|--------|------|------|------|-------|
| GOOGL | 7 | ~$296 | $349.94 | $2,449.58 | +$378.11 | +18.2% |
| MSFT | 4 | ~$405 | $424.46 | $1,697.84 | +$77.30 | +4.8% |
| NVDA | 7 | ~$188 | $209.25 | $1,464.75 | +$147.32 | +11.2% |
| PG | 5 | ~$167 | $146.46 | $732.30 | -$104.60 | -12.5% |
| BABA | 5 | ~$169 | $130.43 | $652.15 | -$195.35 | -23.0% |
| CRCL | 6 | ~$132 | $95.56 | $573.36 | -$221.64 | -27.8% |

**美股合计：$7,569.98**

## 加密货币

| 币种 | 数量 | 现价 | 市值 | 盈亏 | 盈亏% |
|------|------|------|------|------|-------|
| ETH | ~0.26 | $2,078.17 | $540.32 | -$459.68 | -45.9% |
| SOL | ~3 | $78.91 | $236.73 | -$531.46 | -69.2% |
| SHIBxM | ~0.68 | ~$6.04 | $4.11 | -$13.71 | -76.9% |

**加密合计：$781.16**

---

**投资组合总市值：$8,351.14 USD**

## 笔记
- Notion page_id: 349637d0-1bf0-81a7-9476-ef7cf397b54f
- 关注板块：科技股（AI/半导体）、中概股、加密货币
"""

with open(os.path.join(invest_dir, '持仓.md'), 'w', encoding='utf-8') as f:
    f.write(holdings)
print("Created: 投资/持仓.md")

# 3. Remove old wiki/投资-概览.md (since moved)
old_wiki = os.path.join(vault, 'wiki', '投资-概览.md')
if os.path.exists(old_wiki):
    os.remove(old_wiki)
    print("Removed: wiki/投资-概览.md (moved to 投资/)")

# 4. Update index.md
index_path = os.path.join(vault, 'index.md')
with open(index_path, 'r', encoding='utf-8') as f:
    index_content = f.read()

# Replace old wiki reference with new structure
old_invest_ref = "- [[wiki/投资-概览]] - 个人投资概览，包含持仓数据"
new_invest_ref = """## 📁 投资/
- [[投资/概览]] - 个人投资概览，包含持仓数据
- [[投资/持仓]] - 详细持仓明细（股票 + 加密货币）"""

index_content = index_content.replace(old_invest_ref, new_invest_ref)

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(index_content)
print("Updated: index.md")

print("\nDone!")