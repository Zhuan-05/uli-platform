// Original site data - untouched by ULI.
const PRODUCTS = [
  { name: "Brass Fitting", price: "$4.20" },
  { name: "Steel Bracket", price: "$2.75" },
  { name: "Copper Coil", price: "$12.00" },
  { name: "Alloy Plate", price: "$8.50" },
  { name: "Rubber Gasket", price: "$1.10" },
  { name: "Ceramic Spacer", price: "$3.30" },
];

const list = document.getElementById("products");
for (const p of PRODUCTS) {
  const li = document.createElement("li");
  li.innerHTML = `<div>${p.name}</div><div class="price">${p.price}</div>`;
  list.appendChild(li);
}
