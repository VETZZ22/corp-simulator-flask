document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.addEventListener('click', () => {
            button.classList.add('clicked');
            setTimeout(() => button.classList.remove('clicked'), 250);
        });
    });
});
