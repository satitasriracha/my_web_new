console.log('cart.js loaded');

document.addEventListener('click', function (e) {
    const btn = e.target.closest('.add-to-cart');
    if (!btn) return;

    e.preventDefault();
    const id = btn.dataset.id;

    fetch(`/cart/add/${id}/`)   // 👈 ใช้ GET
        .then(res => res.json())
        .then(data => {
            const badge = document.getElementById('cartCount');
            if (!badge) return;

            badge.innerText = data.total_items;
            badge.style.display = 'inline-block';
            badge.classList.add('bounce');
            setTimeout(() => badge.classList.remove('bounce'), 300);
        })
        .catch(err => console.error(err));
});
