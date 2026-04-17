# 📊 Retail Analytics Guide for Shopkeepers
## VoiceSQL Kirana Intelligence

Your system has **13 powerful analytics engines** to help you make smarter business decisions. This guide shows you what to ask and what insights you'll get.

---

## 🎯 Quick Start Examples

### 1️⃣ **Profit Analysis** — "Subse zyada profit kaun sa item de raha hai?"
**What You'll Get:**
- Top 10 most profitable items
- Profit amount per item
- Profit margin percentage (profit/cost × 100)
- Weekly/monthly trends

**Other Ways to Ask:**
- "Profit batao" (Tell me about profit)
- "Kaun sa maal se sab se zyada munafa?" (Which item gives most profit?)
- "Margin kya hai?" (What's the margin?)
- "Profit trend" (Profit analysis)

**Example Output:**
```
📈 PROFIT ANALYSIS (Last 30 Days)

Item          Quantity  Profit    Margin %
────────────────────────────────────────
Biscuit       45        ₹450      15%
Milk          32        ₹320      20%
Oil           12        ₹240      25%
Atta          28        ₹140      10%

💡 Insight: Oil gives highest margin. Increase stock!
```

---

### 2️⃣ **Festival Sales Trends** — "Diwali mein kya bikta hai?"
**What You'll Get:**
- Top-selling items during that festival
- Sales comparison with normal days
- Sales spike percentage
- Suggested stock increase amounts

**Other Ways to Ask:**
- "Holi mein sales kya tha?" (What were Holi sales?)
- "Diwali mein sabse zyada kya bika?" (What sold most during Diwali?)
- "Christmas ke time kaunsa item chal raha tha?" (Which items sold during Christmas?)

**Example Output:**
```
🎉 FESTIVAL TREND - DIWALI

Item          Normal Sales  Diwali Sales  Spike %  Suggest Stock
────────────────────────────────────────────────────────────────
Biscuit       20/day        120/day      +500%   Stock 600 units
Snacks        15/day        90/day       +500%   Stock 450 units
Oil           8/day         45/day       +460%   Stock 225 units
Chini         10/day        35/day       +250%   Stock 175 units

💡 Action: Diwali is coming! Stock up on snacks and biscuits.
```

---

### 3️⃣ **Weather-Based Insights** — "Baarish mein kya bikta hai?"
**What You'll Get:**
- Items that sell more in that season
- Weather-sales correlation
- Restock recommendations

**Other Ways to Ask:**
- "Garmi mein kaunsa item chal raha tha?" (What sells in summer?)
- "Sardi mein inventory kya hona chahiye?" (What inventory for winter?)
- "Mausam ke hisaab se kya stocking karu?" (Stock based on weather?)

**Example Output:**
```
🌦️ WEATHER-BASED TRENDS - RAINY SEASON

Item           Sales Pattern    Recommendation
──────────────────────────────────────────────
Umbrella       +80% in rain     Stock 200 units
Oil/Ghee       +40%             Stock more
Tea/Coffee     +60%             High demand!
Biscuits       -20%             Reduce stock

💡 Action: Stock umbrellas NOW before monsoon!
```

---

### 4️⃣ **Dead Stock Detection** — "Kaun sa maal nahi bik raha?"
**What You'll Get:**
- Items not sold in last 30 days
- How long unsold
- Suggestions (discount/bundle/remove)

**Other Ways to Ask:**
- "Purana stock kaunsa hai?" (What's old stock?)
- "Kaunsa item slow nikle raha hai?" (What's slow-moving?)
- "Dead stock dikha do" (Show unsold items)

**Example Output:**
```
⚠️ DEAD STOCK ALERT

Item           Days Unsold  Last Sold   Action
─────────────────────────────────────────────
Mango (old)    45 days     Feb 20      DISCOUNT 20%
Potato         32 days     Feb 28      BUNDLE: Aloo-Pyaaz combo
Garlic         28 days     Mar 5       DISCOUNT 15%

💡 Action: Discount old mango, bundle potato!
```

---

### 5️⃣ **Customer Buying Patterns** — "Kaunsa ghar kya regularly kharidta hai?"
**What You'll Get:**
- Which customers buy what regularly
- Purchase frequency
- Predictions for next week

**Other Ways to Ask:**
- "Customer pattern batao" (Show customer patterns)
- "Regular customer kya lete hain?" (What do regular customers buy?)
- "Customer X ko kya chahiye?" (What does customer X need?)

**Example Output:**
```
👥 CUSTOMER BUYING PATTERNS

Customer       Regular Items        Frequency   Prediction
───────────────────────────────────────────────────────
Sharma Bhaiya  Atta, Doodh, Chini   3x/week    Needs 2kg Atta soon
Gupta Aunty    Sabzi, Oil           2x/week    Auto-order Oil?
Patel Family   Biscuit, Chai        Daily      Stock for them daily

💡 Action: Reserve items for regular customers. Predict orders!
```

---

### 6️⃣ **Smart Reorder Recommendations** — "Kitna order karna chahiye?"
**What You'll Get:**
- Optimal reorder quantity
- Reorder timing
- Safety stock suggestion
- Cost-efficient bulk orders

**Other Ways to Ask:**
- "Stock kab khatam hoga?" (When will stock run out?)
- "Kya order lagao?" (Should I order?)
- "Kitne din ka stock bacha hai?" (How many days of stock left?)

**Example Output:**
```
📦 SMART REORDER RECOMMENDATIONS

Item        Current Stock  Daily Usage  Days Left  Reorder Now?  Order Qty
────────────────────────────────────────────────────────────────────────
Atta        20kg           5kg/day      4 days     YES ✓         50kg
Oil         8L             2L/day       4 days     YES ✓         20L
Biscuit     150pcs         30/day       5 days     NO            200pcs
Chai        2kg            0.5kg/day    4 days     YES ✓         10kg

💡 Action: Order Atta & Oil TODAY before stock runs out!
```

---

### 7️⃣ **Sales Trends** — "Pichle 7 din ka sales kya tha?"
**What You'll Get:**
- Daily revenue for past N days
- Peak sales day
- Average revenue

**Other Ways to Ask:**
- "Sales batao" (Tell me about sales)
- "Last hafte ka bikri kya tha?" (What were last week's sales?)
- "Din din sales dekho" (Day-by-day sales)

**Example Output:**
```
📈 SALES TREND - LAST 7 DAYS

Day           Revenue   Orders  Peak Item
──────────────────────────────────────────
Monday        ₹4,200    42      Atta
Tuesday       ₹3,800    38      Milk
Wednesday     ₹5,200    52      Biscuit ↑
Thursday      ₹4,500    45      Mix
Friday        ₹6,100    61      Biscuit ↑
Saturday      ₹7,200    72      Weekend ↑↑
Sunday        ₹6,800    68      Weekend ↑↑

📊 Total: ₹37,800 | Avg: ₹5,400/day | Peak: Saturday
💡 Insight: Weekends are 40% busier!
```

---

### 8️⃣ **Hourly Rush Patterns** — "Kaunse waqt sabse zyada bheed hoti hai?"
**What You'll Get:**
- Busiest hours of the day
- Customer traffic by hour
- Staffing recommendations

**Other Ways to Ask:**
- "Peak time kaunsa hai?" (When's peak time?)
- "Sabse busy kaun sa baje?" (Which time is busiest?)
- "Hourly sales kya?" (What are hourly sales?)

**Example Output:**
```
🏪 HOURLY RUSH PATTERN

Time       Customers   Revenue   Busy Level
────────────────────────────────────────────
6-7 AM     45          ₹900      PEAK ↑↑↑
7-8 AM     38          ₹760      PEAK ↑↑
8-9 AM     25          ₹500      Normal
9-12 PM    80          ₹1,600    PEAK ↑↑↑
12-4 PM    30          ₹600      Slow
4-6 PM     90          ₹1,800    PEAK ↑↑
6-9 PM     100         ₹2,000    VERY PEAK ↑↑↑
9-12 PM    40          ₹800      Normal

💡 Action: Hire staff 6-8 AM, 12-6 PM, 6-9 PM!
```

---

### 9️⃣ **Product Demand** — "Sabse zyada kya bik raha hai?"
**What You'll Get:**
- Top 10 products by sales
- Sales quantity and trend

**Other Ways to Ask:**
- "Popular item kaunsa?" (Which is popular?)
- "Most demanded item?" (Highest demand?)
- "Kya-kya bik raha hai?" (What's selling?)

**Example Output:**
```
🏆 TOP 10 PRODUCTS (By Sales)

Rank  Item      Quantity  Trend
──────────────────────────────
1     Biscuit   320/mo    ↑↑↑
2     Atta      180/mo    ↑
3     Oil       95/mo     →
4     Milk      130/mo    ↑↑
5     Doodh     110/mo    ↑
6     Chai      95/mo     →
7     Chawal    75/mo     ↓
8     Dal       65/mo     ↓
9     Chini     55/mo     →
10    Namak     45/mo     ↓

💡 Insight: Biscuit is your star! Milk trending up!
```

---

### 🔟 **Market Basket Analysis** — "Log kya saath mein kharidte hain?"
**What You'll Get:**
- Items frequently bought together
- Cross-sell opportunities
- Bundle ideas

**Other Ways to Ask:**
- "Combo suggestions?" (Which combos sell?)
- "Saath mein kya bikta hai?" (What sells together?)
- "Bundle idea do" (Give bundle ideas)

**Example Output:**
```
🛒 MARKET BASKET (Items Bought Together)

Common Combos                    Frequency
────────────────────────────────────────
Atta + Oil                       65%
Milk + Biscuit                   72%
Chawal + Dal                     58%
Chai + Biscuit                   80%
Aloo + Pyaaz                     55%
Doodh + Sabun                    42%

💡 Action: Create combo deals!
  - "Aloo + Oil" ← 70% sell together
  - "Milk + Biscuit" ← Premium combo
```

---

### 1️⃣1️⃣ **Customer Segmentation (RFM)** — "Best customer kaun hai?"
**What You'll Get:**
- VIP customers (high value)
- At-risk customers (losing interest)
- New customers

**Other Ways to Ask:**
- "High value customer dikha do" (Show VIP customers)
- "Best customer kaun?" (Who's best?)
- "Loyal customer segment" (Loyal customers)

**Example Output:**
```
👤 CUSTOMER SEGMENTS (RFM Analysis)

VIP (High Value)        Frequent (Regular)    At-Risk (Losing)
──────────────────      ──────────────────    ─────────────────
Sharma (₹45K spent)     Gupta (2x/week)       Patel (No visit 2wks)
Desai (₹38K spent)      Singh (3x/week)       Khan (Bought less)
Verma (₹32K spent)      Mehta (Daily)         Rao (Gap increasing)

💡 Action: 
- Offer VIP discounts to Sharma, Desai
- Give loyalty rewards to Gupta, Singh
- Call Patel, Khan to check in
```

---

### 1️⃣2️⃣ **Churn Prediction** — "Kaunsa customer nahi aaya bahut time se?"
**What You'll Get:**
- Customers likely to stop coming
- Churn risk score
- Win-back suggestions

**Other Ways to Ask:**
- "Gayab customer?" (Missing customers?)
- "Churn prediction" (Who might leave?)
- "Dormant account?" (Inactive customers?)

**Example Output:**
```
🚨 CHURN RISK

Customer    Last Visit   Days Gap   Risk Level   Action
──────────────────────────────────────────────────────
Patel       Feb 10       28 days    HIGH ⚠️     CALL TODAY
Khan        Feb 20       18 days    MEDIUM ⚠    CALL SOON
Rao         Feb 25       13 days    MEDIUM ⚠    SPECIAL OFFER

💡 Action: Call Patel immediately! Offer special discount.
```

---

### 1️⃣3️⃣ **Stock Adequacy** — "Kitne din ka stock bacha hai?"
**What You'll Get:**
- How many days each item will last
- Low stock alerts
- Reorder urgency

**Other Ways to Ask:**
- "Stock kab khatam?" (When's stock running out?)
- "Kitne din chalega?" (How many days will it last?)
- "Low stock alert" (What's running low?)

**Example Output:**
```
⏰ STOCK ADEQUACY (Days Remaining)

Item       Current Stock  Daily Use  Days Left  Status
─────────────────────────────────────────────────────
Atta       20kg           5kg        4 days     🔴 URGENT
Oil        8L             2L         4 days     🔴 URGENT
Biscuit    150pcs         30pcs      5 days     🟡 SOON
Milk       12L            3L         4 days     🔴 URGENT
Chai       4kg            0.8kg      5 days     🟡 SOON
Chawal     25kg           4kg        6 days     🟢 OK

Action: Order Atta, Oil, Milk TODAY!
```

---

## 📱 How to Ask (Different Ways)

### **In Hindi (Hinglish):**
```
"Pichle saat din ka sales batao"
"Sabse zyada kya bik raha hai?"
"Diwali mein inventory kya hona chahiye?"
"Mera best customer kaun hai?"
"Dead stock dikha do"
"Profit trend"
"Kaunsa maal nahi bik raha?"
```

### **In English:**
```
"Show me sales trend for last 7 days"
"What's selling the most?"
"How much should I reorder?"
"Dead stock detection"
"Profit analysis"
"Customer patterns"
"Festival trends for Diwali"
```

### **By Voice (using Sarvam AI):**
Just speak naturally! The system understands:
- Mixed Hindi-English
- Devanagari script
- Casual speech

---

## 💡 When to Use Each Analysis

| Situation | Ask For | Benefit |
|-----------|---------|---------|
| **Opening shop** | "Aaj ka stock check" | Know what to focus on |
| **Ordering day** | "Smart reorder" | Don't over/under stock |
| **Festival coming** | "Diwali mein kya bikta?" | Stock correctly |
| **Profit review** | "Profit trend" | Find best sellers |
| **Slow sales** | "Dead stock", "Customer pattern" | Fix what's not selling |
| **Busy hours** | "Hourly rush" | Hire staff smartly |
| **Customer care** | "Best customer", "At-risk customer" | Keep loyal customers |
| **Planning stock** | "Smart reorder", "Stock adequacy" | Avoid stockouts |

---

## 🎯 Top 5 Actions to Take Now

1. **Ask about Dead Stock** → Remove items not selling
2. **Check Profit by Item** → Stock what's profitable
3. **See Festival Trends** → Plan for Diwali/Holi
4. **Customer Analysis** → Reward loyal customers
5. **Hourly Rush** → Hire staff efficiently

---

## 🔍 Advanced Queries

### Predict Next Orders
**"Sharma ke liye next week kya order karo?"**
- Shows what Sharma usually buys
- Predicts next purchase
- Auto-suggest quantity

### Loyalty Program
**"Kaun kaun mera loyal customer hai?"**
- Frequent buyers (VIP) ← Reward them!
- Buy value score
- Retention strategies

### Bundle Strategy
**"Chai aur biscuit saath mein bik rahe hain?"**
- Create combo offers
- Cross-sell ideas
- Margin optimization

### Seasonal Planning
**"Monsoon mein inventory plan karo"**
- Items to increase/decrease
- Expected demand shift
- Stock levels recommend

---

## 📊 Dashboard Features

**Real-time Updates:**
- ✅ Sales as they happen
- ✅ Stock levels
- ✅ Customer visits
- ✅ Profit tracking

**Charts & Graphs:**
- 📈 Sales trends
- 📊 Product performance
- 🎯 Customer segments
- 🌡️ Seasonal patterns

---

## ⚙️ System Setup

**Already Working:**
- ✅ Sarvam Saaras v3 (Voice transcription)
- ✅ 13 Analytics Engines
- ✅ Hinglish Support
- ✅ Real-time Processing

**To Get Started:**
1. Ask any question above
2. System analyzes data
3. Get actionable insights
4. Take smart business decisions

---

## 🆘 Need Help?

**Ask the system:**
- "Help"
- "Analytics guide"
- "What can I ask?"
- "Mujhe samjhao" (Explain to me)

**Common Issues:**
- **No data**: System needs 7+ days of transaction data
- **Slow response**: Refresh after 5 mins
- **Voice not working**: Check microphone permission

---

## 📞 Support

For issues:
1. Check if SARVAM_API_KEY is set in .env
2. Ensure Groq API key is active
3. Verify database has transaction data

**Test Command:**
```bash
python test_sarvam.py
python main.py --api
```

---

**Last Updated:** April 8, 2026  
**System Version:** VoiceSQL v1.0 with 13 Analytics Engines  
**Language Support:** Hinglish (Hindi + English mixed), Devanagari script

Happy Analytics! 🚀
