from flask import Flask, request, send_file, render_template_string
import io
from generate_cmr import generate_full_cmr

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CMR 运单生成器</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; color: #1a1a2e; }
  header { background: #1a3c5e; color: white; padding: 18px 32px; display: flex; align-items: center; gap: 14px; }
  header h1 { font-size: 1.3rem; font-weight: 600; }
  header .badge { background: #e8b84b; color: #1a1a2e; font-size: 0.7rem; font-weight: 700; 
    padding: 3px 8px; border-radius: 20px; letter-spacing: .5px; }
  .container { max-width: 960px; margin: 30px auto; padding: 0 16px 60px; }
  .section { background: white; border-radius: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.1);
    margin-bottom: 20px; overflow: hidden; }
  .section-header { background: #1a3c5e; color: white; padding: 10px 18px; font-size: .85rem;
    font-weight: 600; letter-spacing: .3px; }
  .section-body { padding: 18px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .section-body.wide { grid-template-columns: 1fr; }
  .field { display: flex; flex-direction: column; gap: 4px; }
  .field.span2 { grid-column: span 2; }
  label { font-size: .78rem; color: #5a6a7a; font-weight: 600; }
  label span { color: #aaa; font-weight: 400; font-size: .72rem; margin-left: 4px; }
  input, textarea, select {
    border: 1.5px solid #dde3ea; border-radius: 6px; padding: 8px 10px;
    font-size: .9rem; transition: border .15s; background: #fafbfc; width: 100%;
  }
  input:focus, textarea:focus, select:focus {
    outline: none; border-color: #1a3c5e; background: white;
  }
  textarea { resize: vertical; min-height: 62px; }

  /* Goods table */
  .goods-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
  .goods-table th { background: #f0f2f5; padding: 7px 8px; text-align: left;
    font-size: .73rem; color: #5a6a7a; border-bottom: 2px solid #dde3ea; }
  .goods-table td { padding: 5px 4px; border-bottom: 1px solid #f0f2f5; }
  .goods-table input { padding: 5px 7px; font-size: .82rem; }
  .add-row { background: none; border: 1.5px dashed #1a3c5e; color: #1a3c5e;
    padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: .8rem;
    margin-top: 8px; transition: background .15s; }
  .add-row:hover { background: #eef3f9; }

  .radio-group { display: flex; gap: 20px; align-items: center; padding: 4px 0; }
  .radio-group label { font-size: .88rem; color: #1a1a2e; font-weight: 400;
    display: flex; align-items: center; gap: 6px; cursor: pointer; }

  .submit-bar { position: sticky; bottom: 0; background: white;
    border-top: 1px solid #dde3ea; padding: 14px 32px; display: flex;
    justify-content: flex-end; gap: 12px; z-index: 10; }
  .btn-primary { background: #1a3c5e; color: white; border: none; padding: 11px 32px;
    border-radius: 7px; font-size: .95rem; font-weight: 600; cursor: pointer;
    transition: background .15s; }
  .btn-primary:hover { background: #245080; }
  .btn-reset { background: white; color: #5a6a7a; border: 1.5px solid #dde3ea;
    padding: 11px 20px; border-radius: 7px; font-size: .9rem; cursor: pointer; }
</style>
</head>
<body>
<header>
  <div>
    <h1>CMR 国际运单生成器</h1>
    <div style="font-size:.78rem;opacity:.75;margin-top:2px">International Consignment Note · Convention CMR</div>
  </div>
  <div class="badge">IRU 1976</div>
</header>

<form method="POST" action="/generate">
<div class="container">

  <!-- 1. Parties -->
  <div class="section">
    <div class="section-header">📦 1  当事方信息 / Parties</div>
    <div class="section-body">
      <div class="field span2">
        <label>运单编号 Note No <span>/ No du connaissement</span></label>
        <input name="note_number" placeholder="e.g. 24382">
      </div>
      <div class="field">
        <label>发货人 Sender <span>名称·地址·国家</span></label>
        <textarea name="sender" placeholder="公司名称&#10;地址&#10;国家"></textarea>
      </div>
      <div class="field">
        <label>收货人 Consignee <span>名称·地址·国家</span></label>
        <textarea name="consignee" placeholder="公司名称&#10;地址&#10;国家"></textarea>
      </div>
      <div class="field">
        <label>交货地点 Place of Delivery <span>地点·国家</span></label>
        <input name="delivery_place" placeholder="城市, 国家">
      </div>
      <div class="field">
        <label>承运地点及日期 Pickup Place & Date</label>
        <input name="pickup_place" placeholder="城市, 国家, 日期">
      </div>
    </div>
  </div>

  <!-- 2. Carrier -->
  <div class="section">
    <div class="section-header">🚛 16–17  承运人信息 / Carriers</div>
    <div class="section-body">
      <div class="field">
        <label>承运人 Carrier <span>名称·地址·国家</span></label>
        <textarea name="carrier" placeholder="运输公司名称&#10;地址&#10;国家"></textarea>
      </div>
      <div class="field">
        <label>后续承运人 Successive Carriers <span>可选</span></label>
        <textarea name="successive_carriers" placeholder="如有后续承运方，请填写"></textarea>
      </div>
    </div>
  </div>

  <!-- 3. Goods -->
  <div class="section">
    <div class="section-header">📋 6–12  货物明细 / Goods</div>
    <div class="section-body wide" style="padding:18px">
      <table class="goods-table" id="goods-table">
        <thead>
          <tr>
            <th>标记号码<br>Marks & Nos</th>
            <th>包装件数<br>Packages</th>
            <th>包装方式<br>Packing</th>
            <th>货物描述<br>Description</th>
            <th>统计编号<br>Stat No</th>
            <th>毛重 kg<br>Weight</th>
            <th>体积 m³<br>Volume</th>
            <th>ADR级别<br>Class</th>
            <th>危险品编号<br>ADR No</th>
          </tr>
        </thead>
        <tbody id="goods-body">
          <tr>
            <td><input name="marks[]" placeholder="Marks"></td>
            <td><input name="packages[]" placeholder="0"></td>
            <td><input name="packing[]" placeholder="Pallets"></td>
            <td><input name="description[]" placeholder="货物描述"></td>
            <td><input name="stat_no[]" placeholder=""></td>
            <td><input name="weight[]" placeholder="0.00"></td>
            <td><input name="volume[]" placeholder="0.00"></td>
            <td><input name="adr_class[]" placeholder=""></td>
            <td><input name="adr_number[]" placeholder=""></td>
          </tr>
        </tbody>
      </table>
      <button type="button" class="add-row" onclick="addRow()">＋ 添加一行货物</button>
    </div>
  </div>

  <!-- 4. Documents & Instructions -->
  <div class="section">
    <div class="section-header">📎 5 · 13–15  单据·指示·协议 / Documents & Instructions</div>
    <div class="section-body">
      <div class="field">
        <label>附随单据 Documents Attached <span>box 5</span></label>
        <input name="documents" placeholder="CMR, Invoice, Packing List...">
      </div>
      <div class="field">
        <label>发货人指示 Sender's Instructions <span>box 13</span></label>
        <textarea name="sender_instructions" placeholder="特殊运输指示..."></textarea>
      </div>
      <div class="field span2">
        <label>特殊协议 Special Agreements <span>box 14</span></label>
        <textarea name="special_agreements" placeholder="特殊条款..." style="min-height:48px"></textarea>
      </div>
      <div class="field span2">
        <label>运费付款方式 Payment <span>box 15</span></label>
        <div class="radio-group">
          <label><input type="radio" name="carriage_paid" value="paid" checked> 
            ✅ 预付 Carriage Paid (Franco)</label>
          <label><input type="radio" name="carriage_paid" value="forward"> 
            到付 Carriage Forward (Non franco)</label>
        </div>
      </div>
    </div>
  </div>

  <!-- 5. Charges -->
  <div class="section">
    <div class="section-header">💰 19–24  费用明细 / Charges</div>
    <div class="section-body">
      <div class="field">
        <label>货币 Currency</label>
        <select name="currency">
          <option value="EUR">EUR – 欧元</option>
          <option value="USD">USD – 美元</option>
          <option value="CNY">CNY – 人民币</option>
          <option value="GBP">GBP – 英镑</option>
          <option value="CHF">CHF – 瑞士法郎</option>
        </select>
      </div>
      <div class="field">
        <label>运费 Carriage Charges</label>
        <input name="carriage_charges" placeholder="0.00">
      </div>
      <div class="field">
        <label>减扣 Deductions</label>
        <input name="deductions" placeholder="0.00">
      </div>
      <div class="field">
        <label>差额 Balance</label>
        <input name="balance" placeholder="0.00">
      </div>
      <div class="field">
        <label>附加费 Supplementary Charges</label>
        <input name="supplementary_charges" placeholder="0.00">
      </div>
      <div class="field">
        <label>其他费用 Other Charges</label>
        <input name="other_charges" placeholder="0.00">
      </div>
      <div class="field">
        <label>总计 TOTAL</label>
        <input name="total" placeholder="0.00">
      </div>
      <div class="field">
        <label>货到付款 Cash on Delivery</label>
        <input name="cash_on_delivery" placeholder="0.00">
      </div>
    </div>
  </div>

  <!-- 6. Signatures & issuance -->
  <div class="section">
    <div class="section-header">✍️ 签署信息 / Signatures & Issuance</div>
    <div class="section-body">
      <div class="field">
        <label>制单地点 Established in</label>
        <input name="established_at" placeholder="城市">
      </div>
      <div class="field">
        <label>制单日期 Date</label>
        <input name="established_date" type="date">
      </div>
      <div class="field">
        <label>发货人签章 Sender Signature/Stamp</label>
        <input name="sender_signature" placeholder="签名或公司章">
      </div>
      <div class="field">
        <label>承运人签章 Carrier Signature/Stamp</label>
        <input name="carrier_signature" placeholder="签名或公司章">
      </div>
      <div class="field">
        <label>收货地点 Received at (Place)</label>
        <input name="received_place" placeholder="城市">
      </div>
      <div class="field">
        <label>收货日期 Received on (Date)</label>
        <input name="received_date" type="date">
      </div>
      <div class="field span2">
        <label>收货人签章 Consignee Signature/Stamp <span>box 24</span></label>
        <input name="consignee_signature" placeholder="签名或公司章">
      </div>
      <div class="field span2">
        <label>承运人备注 Carrier's Reservations <span>box 18, 可选</span></label>
        <textarea name="carrier_reservations" placeholder="货物状态备注、保留声明等..."></textarea>
      </div>
    </div>
  </div>

</div><!-- /container -->

<div class="submit-bar">
  <button type="reset" class="btn-reset">🔄 重置表单</button>
  <button type="submit" class="btn-primary">📄 生成 PDF 运单 (3份)</button>
</div>
</form>

<script>
function addRow() {
  const tbody = document.getElementById('goods-body');
  const first = tbody.querySelector('tr');
  const newRow = first.cloneNode(true);
  newRow.querySelectorAll('input').forEach(i => i.value = '');
  tbody.appendChild(newRow);
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/generate", methods=["POST"])
def generate():
    f = request.form

    # Build goods list
    marks = f.getlist("marks[]")
    packages = f.getlist("packages[]")
    packing = f.getlist("packing[]")
    description = f.getlist("description[]")
    stat_no = f.getlist("stat_no[]")
    weight = f.getlist("weight[]")
    volume = f.getlist("volume[]")
    adr_class = f.getlist("adr_class[]")
    adr_number = f.getlist("adr_number[]")

    goods = []
    for i in range(len(marks)):
        goods.append({
            "marks": marks[i] if i < len(marks) else "",
            "packages": packages[i] if i < len(packages) else "",
            "packing": packing[i] if i < len(packing) else "",
            "description": description[i] if i < len(description) else "",
            "stat_no": stat_no[i] if i < len(stat_no) else "",
            "weight": weight[i] if i < len(weight) else "",
            "volume": volume[i] if i < len(volume) else "",
            "adr_class": adr_class[i] if i < len(adr_class) else "",
            "adr_number": adr_number[i] if i < len(adr_number) else "",
        })

    data = {
        "note_number": f.get("note_number", ""),
        "sender": f.get("sender", ""),
        "consignee": f.get("consignee", ""),
        "delivery_place": f.get("delivery_place", ""),
        "pickup_place": f.get("pickup_place", ""),
        "carrier": f.get("carrier", ""),
        "successive_carriers": f.get("successive_carriers", ""),
        "goods": goods,
        "documents": f.get("documents", ""),
        "sender_instructions": f.get("sender_instructions", ""),
        "special_agreements": f.get("special_agreements", ""),
        "carriage_paid": f.get("carriage_paid", "paid") == "paid",
        "currency": f.get("currency", "EUR"),
        "carriage_charges": f.get("carriage_charges", ""),
        "deductions": f.get("deductions", ""),
        "balance": f.get("balance", ""),
        "supplementary_charges": f.get("supplementary_charges", ""),
        "other_charges": f.get("other_charges", ""),
        "total": f.get("total", ""),
        "cash_on_delivery": f.get("cash_on_delivery", ""),
        "established_at": f.get("established_at", ""),
        "established_date": f.get("established_date", ""),
        "sender_signature": f.get("sender_signature", ""),
        "carrier_signature": f.get("carrier_signature", ""),
        "received_place": f.get("received_place", ""),
        "received_date": f.get("received_date", ""),
        "consignee_signature": f.get("consignee_signature", ""),
        "carrier_reservations": f.get("carrier_reservations", ""),
    }

    pdf_bytes = generate_full_cmr(data)
    note_no = data["note_number"] or "CMR"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"CMR_{note_no}.pdf"
    )

if __name__ == "__main__":
    app.run(debug=True, port=5050)
