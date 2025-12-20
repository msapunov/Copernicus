document.addEventListener("DOMContentLoaded", () => {
    const loginEl = document.getElementById("user_login");
    const login = (loginEl?.dataset.login || "").trim();
    if (!login) return;
    const URL = {
        edit: "user/modal/edit",
        upload: "user/modal/ssh",
        reset: "reset.html"
    };
    const Control = {
        onClick(e) {
            const btn = e.target.closest('button');
            if (!btn) return;
            if (btn.classList.contains('info')) {
                this.viewUser();
            } else if (btn.classList.contains('accept')) {
                this.editUser();
            } else if (btn.classList.contains('reset')) {
                this.resetPassword();
            }
        },
        viewUser() {
            window.ModalFactory.createModal({
                title: 'User Info',
                content: `<p>Showing details for user #${login}</p>`,
                confirmText: 'Close',
                cancelText: ''
            });
        },

        editUser(id) {
            window.ModalFactory.createModal({
                title: 'Accept User',
                content: `<p>Are you sure you want to accept user #${login}?</p>`,
                confirmText: 'Yes, Accept',
                onConfirm: () => console.log(`Accept user ${login}`)
            });
        },

        resetPassword() {
            window.location.href = URL.reset;
        }
    };
    document.addEventListener("click", Control.onClick);
});