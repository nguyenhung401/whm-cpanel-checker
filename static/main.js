// ===============================
// CONFIG API URL
// ===============================

// ⚠️ Nhớ sửa LINK API Render của bạn nếu khác!
// Ví dụ: [https://whm-cpanel-checker.onrender.com/scan](https://whm-cpanel-checker.onrender.com/scan)
const API_URL = window.location.origin + "/scan";

// ===============================
// Đọc file TXT
// ===============================
function readFile(file){
return new Promise((resolve)=>{
const reader = new FileReader();
reader.onload = (e)=>resolve(e.target.result);
reader.readAsText(file);
});
}

// ===============================
// Bắt đầu scan
// ===============================
async function startScan(){
document.getElementById("info").textContent = "⏳ Đang xử lý...";
document.getElementById("resultsBody").innerHTML = "";

```
let text = document.getElementById("textInput").value.trim();

// Nếu có upload file → ưu tiên file
const file = document.getElementById("fileInput").files[0];
if(file){
    text = await readFile(file);
}

if(!text){
    alert("⚠️ Vui lòng dán nội dung hoặc upload file .TXT!");
    return;
}

try{
    const res = await fetch(API_URL, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({text})
    });

    const data = await res.json();
    renderResults(data.results);

    document.getElementById("info").textContent =
        "✅ Hoàn tất (" + data.results.length + " dòng)";

    window.scanResults = data.results;

}catch(err){
    document.getElementById("info").textContent = "❌ Lỗi API: " + err;
}
```

}

// ===============================
// Hiển thị kết quả ra bảng
// ===============================
function renderResults(list){
const tbody = document.getElementById("resultsBody");
tbody.innerHTML = "";

```
for(let r of list){
    let tr = document.createElement("tr");

    tr.innerHTML = `
        <td>${r.host || ""}</td>
        <td>${r.port || ""}</td>
        <td>${r.user || ""}</td>
        <td>${r.type || ""}</td>
        <td class="${r.status === "OK" ? "status-ok" : "status-fail"}">
            ${r.status}
        </td>
        <td>${r.message || ""}</td>
    `;

    tbody.appendChild(tr);
}
```

}

// ===============================
// Tải kết quả thành file CSV
// ===============================
function downloadCSV(){
if(!window.scanResults){
alert("⚠️ Chưa có dữ liệu để xuất CSV!");
return;
}

```
let csv = "host,port,user,type,status,message\n";

window.scanResults.forEach(r=>{
    csv += `${r.host},${r.port},${r.user},${r.type},${r.status},${r.message}\n`;
});

const blob = new Blob([csv], {type:"text/csv"});
const url = URL.createObjectURL(blob);

const a = document.createElement("a");
a.href = url;
a.download = "whm_cpanel_results.csv";
a.click();
```

}
