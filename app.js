
const productGrid = document.getElementById('productGrid');
const searchInput = document.getElementById('searchInput');
const productCount = document.getElementById('productCount');

let products = [];

function formatVND(value){
    return Number(value).toLocaleString('vi-VN') + ' đ';
}

function render(list){

    productCount.textContent =
        'Sản phẩm: ' + list.length;

    productGrid.innerHTML = '';

    list.forEach(p => {

        const card = document.createElement('div');

        card.className = 'card';

        card.innerHTML = `
            <img src="${p.Image_URL || \"https://via.placeholder.com/600x600?text=No+Image\"}" alt="" onerror="this.src=\"https://via.placeholder.com/600x600?text=No+Image\"">
            <div class="card-body">
                <div class="code">${p.Code}</div>
                <div class="card-title">${p.ProductName}</div>
                <div class="category">${p.Category || ""}</div>
                <div class="price">
                    ${formatVND(p.SalePrice)}
                </div>
            </div>
        `;

        productGrid.appendChild(card);
    });
}

fetch('products.json')
    .then(r => r.json())
    .then(data => {

        products = data;

        render(products);

        searchInput.addEventListener('input', () => {

            const q =
                searchInput.value.toLowerCase();

            const filtered = products.filter(p =>
                (p.ProductName || '')
                    .toLowerCase()
                    .includes(q)
                ||
                (p.Code || '')
                    .toLowerCase()
                    .includes(q)
            );

            render(filtered);
        });
    });
