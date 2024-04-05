const TABLE_ID = '#table-tasks';


function actions_task_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    let tags = [
        `
        <a
                href="/task/${row.id}"
                title="Страница задачи"
        >
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
        `,
        `
        <a
                class="text-success-emphasis"
                href="/task/${row.id}/update"
                title="Редактировать"
        >
            <i class="bi bi-pencil-square"></i>
        </a>
        `
    ];
    if (row.is_enabled) {
        tags.push(
            `
            <button
                    class="btn text-success p-0"
                    title="Запуск"
                    data-url="/api/task/${row.id}/action/run"
                    data-method="POST"
            >
                <i class="bi bi-caret-right-square-fill"></i>
            </button>
            `
        );
    }
    if (row.last_started_run_seq != null) {
        tags.push(
            `
            <a
                    href="/task/${row.id}/run/${row.last_started_run_seq}"
                    title="Страница последнего запуска"
            >
                <i class="bi bi-terminal"></i>
            </a>
            `
        );
    }
    tags.push(
        `
        <button
                class="btn text-danger p-0"
                title="Удалить"
                data-url="/api/task/${row.id}/delete"
                data-method="DELETE"
                data-confirm-text="Удалить задачу?"
                data-callback="delete_table_row('${TABLE_ID}', ${row.id})"
        >
            <i class="bi bi-trash3"></i>
        </button>
        `
    );
    return tags.join("");
}


function work_status_task_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }

    let result = get_work_status_task_widget(data);
    return `
        <div class="d-flex justify-content-center">
            ${result}
        </div>
    `;
}


function task_name_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    return `<a href="/task/${row.id}">${data}</a>`;
}


$(function() {
    new DataTable(TABLE_ID, {
        ajax: {
            url: '/api/tasks',
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            {
                render: actions_task_render,
                orderable: false,
                title: `
                    <a
                            class="btn btn-success btn-sm"
                            title="Создать задачу"
                            href="/task/create"
                            role="button"
                    >
                        <i class="bi bi-plus-lg"></i>
                    </a>
                `,
            },
            {
                data: 'last_work_status',
                render: work_status_task_render,
                orderable: false,
                title: 'Статус',
            },
            { data: 'id', title: 'Ид.', },
            { data: 'name', title: 'Название', render: task_name_render, },
            { data: 'description', title: 'Описание', },
            { data: 'cron', title: 'Расписание', },
            { data: 'is_enabled', title: 'Активный', render: bool_render, },
            { data: 'is_infinite', title: 'Бесконечный', render: bool_render, },
            { data: 'command', title: 'Команда', },
            { data: 'last_started_run_start_date', title: 'Последний запуск', render: date_render, },
            { data: 'number_of_runs', title: 'Запуски', },
        ],
        order: [
            // Сортировка по возрастанию id
            [2, "asc"],
        ],
        initComplete: tableInitComplete,
        rowCallback: function(row, data, displayNum, displayIndex, dataIndex) {
            $(row).toggleClass("row-disabled", !data.is_enabled);
        },
        language: LANG_DATATABLES,
    });
});
