const API_BASE = "";

const authSection = document.getElementById("authSection");
const dashboardSection = document.getElementById("dashboardSection");
const logoutButton = document.getElementById("logoutButton");

const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");

const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");

const authMessage = document.getElementById("authMessage");
const taskMessage = document.getElementById("taskMessage");

const taskForm = document.getElementById("taskForm");
const taskList = document.getElementById("taskList");
const refreshButton = document.getElementById("refreshButton");


function getToken() {
    return localStorage.getItem("securetask_token");
}


function setToken(token) {
    localStorage.setItem("securetask_token", token);
}


function clearToken() {
    localStorage.removeItem("securetask_token");
}


function showMessage(element, message, isError = false) {
    element.textContent = message;
    element.style.color = isError ? "#dc2626" : "#166534";
}


function showLogin() {
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");

    loginTab.classList.add("active");
    registerTab.classList.remove("active");

    authMessage.textContent = "";
}


function showRegister() {
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");

    loginTab.classList.remove("active");
    registerTab.classList.add("active");

    authMessage.textContent = "";
}


function showDashboard() {
    authSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");
    logoutButton.classList.remove("hidden");

    loadTasks();
}


function showAuthentication() {
    authSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    logoutButton.classList.add("hidden");

    showLogin();
}


async function apiRequest(url, options = {}) {
    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers
    });

    let data = null;

    try {
        data = await response.json();
    } catch {
        data = null;
    }

    if (!response.ok) {
        let message = "Request failed.";

        if (data) {
            if (typeof data.detail === "string") {
                message = data.detail;
            } else if (Array.isArray(data.detail)) {
                message = data.detail
                    .map(error => error.msg)
                    .join(", ");
            }
        }

        throw new Error(message);
    }

    return data;
}


loginTab.addEventListener("click", showLogin);

registerTab.addEventListener("click", showRegister);


registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("registerUsername").value;
    const email = document.getElementById("registerEmail").value;
    const password = document.getElementById("registerPassword").value;

    try {
        await apiRequest("/register", {
            method: "POST",
            body: JSON.stringify({
                username,
                email,
                password
            })
        });

        showMessage(
            authMessage,
            "Account created successfully. You can now login."
        );

        registerForm.reset();

        setTimeout(() => {
            showLogin();
        }, 1000);

    } catch (error) {
        showMessage(
            authMessage,
            error.message,
            true
        );
    }
});


loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("loginUsername").value;
    const password = document.getElementById("loginPassword").value;

    try {
        const data = await apiRequest("/login", {
            method: "POST",
            body: JSON.stringify({
                username,
                password
            })
        });

        setToken(data.access_token);

        loginForm.reset();

        showDashboard();

    } catch (error) {
        showMessage(
            authMessage,
            error.message,
            true
        );
    }
});


taskForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const title = document.getElementById("taskTitle").value;
    const description =
        document.getElementById("taskDescription").value;

    try {
        await apiRequest("/tasks", {
            method: "POST",
            body: JSON.stringify({
                title,
                description: description || null
            })
        });

        taskForm.reset();

        showMessage(
            taskMessage,
            "Task created successfully."
        );

        loadTasks();

    } catch (error) {
        showMessage(
            taskMessage,
            error.message,
            true
        );
    }
});


async function loadTasks() {
    try {
        const tasks = await apiRequest("/tasks");

        displayTasks(tasks);

    } catch (error) {

        if (
            error.message.toLowerCase().includes("credentials") ||
            error.message.toLowerCase().includes("unauthorized")
        ) {
            clearToken();
            showAuthentication();
            return;
        }

        taskList.innerHTML = `
            <p class="empty-message">
                Unable to load tasks.
            </p>
        `;
    }
}


function displayTasks(tasks) {

    if (!tasks || tasks.length === 0) {
        taskList.innerHTML = `
            <p class="empty-message">
                No tasks yet. Create your first task above.
            </p>
        `;

        return;
    }

    taskList.innerHTML = "";

    tasks.forEach(task => {

        const taskElement = document.createElement("div");

        taskElement.className =
            task.completed ? "task completed" : "task";

        const statusClass =
            task.completed
                ? "status-complete"
                : "status-pending";

        const statusText =
            task.completed
                ? "Completed"
                : "Pending";

        taskElement.innerHTML = `
            <h3>${escapeHtml(task.title)}</h3>

            <p>
                ${escapeHtml(task.description || "No description")}
            </p>

            <span class="task-status ${statusClass}">
                ${statusText}
            </span>

            <div class="task-actions">

                ${
                    task.completed
                    ? ""
                    : `
                        <button
                            class="complete-button"
                            onclick="completeTask(${task.id})"
                        >
                            Mark Complete
                        </button>
                    `
                }

                <button
                    class="delete-button"
                    onclick="deleteTask(${task.id})"
                >
                    Delete
                </button>

            </div>
        `;

        taskList.appendChild(taskElement);
    });
}


async function completeTask(taskId) {

    try {

        await apiRequest(`/tasks/${taskId}`, {
            method: "PUT",
            body: JSON.stringify({
                completed: true
            })
        });

        loadTasks();

    } catch (error) {

        showMessage(
            taskMessage,
            error.message,
            true
        );
    }
}


async function deleteTask(taskId) {

    const confirmed = confirm(
        "Are you sure you want to delete this task?"
    );

    if (!confirmed) {
        return;
    }

    try {

        await apiRequest(`/tasks/${taskId}`, {
            method: "DELETE"
        });

        showMessage(
            taskMessage,
            "Task deleted successfully."
        );

        loadTasks();

    } catch (error) {

        showMessage(
            taskMessage,
            error.message,
            true
        );
    }
}


function escapeHtml(value) {

    const div = document.createElement("div");

    div.textContent = value;

    return div.innerHTML;
}


logoutButton.addEventListener("click", () => {

    clearToken();

    taskList.innerHTML = `
        <p class="empty-message">
            No tasks yet.
        </p>
    `;

    showAuthentication();
});


refreshButton.addEventListener("click", loadTasks);


if (getToken()) {
    showDashboard();
} else {
    showAuthentication();
}