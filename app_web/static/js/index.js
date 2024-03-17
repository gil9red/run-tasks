function actions_task_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    let tags = [
        `
        <a href="/task/${row.id}" target="_blank">
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
        `,
        `
        <button
            class="btn btn-link p-0"
            title="Запуск задачи"
            data-url="/api/task/${row.id}/action/run"
            data-method="POST"
        >
            <i class="bi bi-play-fill text-success"></i>
        </button>
        `,
    ];
    if (row.last_started_run_seq != null) {
        tags.push(
            `<a href="/task/${row.id}/run/${row.last_started_run_seq}" target="_blank">
               <i class="bi bi-terminal"></i>
            </a>`
        );
    }
    return tags.join("");
}

function task_name_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    return `<a href="/task/${row.id}">${data}</a>`;
}

$(function() {
    new DataTable('#table-tasks', {
        ajax: {
            url: '/api/tasks',
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            // TODO: Заполнить title
            { render: actions_task_render, orderable: false, },
            { data: 'id', title: 'id', },
            { data: 'name', title: 'Название', render: task_name_render, },
            { data: 'description', title: 'Описание', },
            { data: 'cron', title: 'Cron', },
            { data: 'is_enabled', title: 'is_enabled', },
            { data: 'is_infinite', title: 'is_infinite', },
            { data: 'command', title: 'command', },
            { data: 'number_of_runs', title: 'number_of_runs', },
        ],
        order: [
            // Сортировка по возрастанию id
            [1, "asc"],
        ],
        language: LANG_DATATABLES,
    });
});
