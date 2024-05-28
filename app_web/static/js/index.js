const TABLE_ID = '#table-tasks';


function actions_task_render(data, type, row, meta) {
    if (type === 'filter') {
        return null;
    }
    let tags = [
        `
        <a
                class="icon-link"
                href="/task/${row.id}"
                title="Страница задачи"
        >
            <i class="bi bi-box-arrow-up-right"></i>
        </a>
        `,
        `
        <a
                class="icon-link text-success-emphasis"
                href="/task/${row.id}/update"
                title="Редактировать"
        >
            <i class="bi bi-pencil-square"></i>
        </a>
        `
    ];
    if (row.is_enabled && row.last_work_status != "in_processed") {
        tags.push(
            `
            <button
                    class="btn text-success p-0"
                    title="Запуск"
                    data-url="/api/task/${row.id}/do-run"
                    data-method="POST"
            >
                <i class="bi bi-caret-right-square-fill"></i>
            </button>
            `
        );
    }
    if (row.last_work_status == "in_processed") {
        tags.push(
            `
            <button
                    class="btn text-warning p-0"
                    title="Остановить запуск #${row.last_started_run_seq}"
                    data-url="/api/task/${row.id}/run/${row.last_started_run_seq}/do-stop"
                    data-method="POST"
            >
                <i class="bi bi-stop-circle"></i>
            </button>
            `
        );
    }
    if (row.last_started_run_seq != null) {
        tags.push(
            `
            <a
                    class="icon-link"
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


function task_name_render(data, type, row, meta) {
    if (type === 'filter') {
        return data;
    }
    return `<a href="/task/${row.id}">${data}</a>`;
}


$(function() {
    let cb_visible_disabled_tasks = "cb_visible_disabled_tasks";

    let table = new DataTable(TABLE_ID, {
        ajax: {
            url: '/api/tasks',
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            {
                data: null, // Явное указание, что тут нет источника данных
                render: actions_task_render,
                orderable: false,
                title: getTableHeaderTitleWithMenu([
                    `
                    <li class="ps-3">
                        <a
                                class="btn btn-success btn-sm"
                                title="Создать задачу"
                                href="/task/create"
                                role="button"
                        >
                            <i class="bi bi-plus-lg"></i>
                        </a>
                    </li>
                    `,
                    `
                    <div class="dropdown-item">
                        <div class="form-check">
                            <input
                                    class="form-check-input column-visible"
                                    type="checkbox"
                                    id="${cb_visible_disabled_tasks}"
                            >
                            <label class="form-check-label w-100" for="${cb_visible_disabled_tasks}">
                                Показывать неактивные задачи
                            </label>
                        </div>
                    </div>
                    `,
                ]),
                width: '70px',
            },
            {
                data: 'last_work_status',
                render: work_status_task_run_render,
                orderable: false,
                title: 'Статус',
            },
            { data: 'id', title: 'Ид.', },
            { data: 'name', title: 'Название', render: task_name_render, },
            { data: 'description', title: 'Описание', visible: false, },
            { data: 'cron', title: 'Расписание', },
            { data: 'is_enabled', title: 'Активный', render: bool_render, },
            { data: 'is_infinite', title: '<i class="bi bi-infinity"></i>', render: bool_render, },
            { data: 'command', title: 'Команда', visible: false, },
            { data: 'last_started_run_start_date', title: 'Последний запуск', render: date_render, },
            { data: 'next_scheduled_date', title: 'Следующий запуск', visible: false, render: date_render, },
            { data: 'number_of_runs', title: 'Запуски', },
        ],
        order: [
            // Сортировка по возрастанию id
            [2, "asc"],
        ],
        rowCallback: function(row, data, displayNum, displayIndex, dataIndex) {
            $(row).toggleClass("row-disabled", !data.is_enabled);
        },
        ...COMMON_PROPS_DATA_TABLE,
    });

    let $cb_visible_disabled_tasks = $(`#${cb_visible_disabled_tasks}`);
    let value_cb_visible_disabled_tasks = localStorage.getItem(cb_visible_disabled_tasks);
    $cb_visible_disabled_tasks.prop(
        'checked',
        // Значение, по-умолчанию, true
        value_cb_visible_disabled_tasks === null
        || value_cb_visible_disabled_tasks == "true"
    );

    table.search.fixed(cb_visible_disabled_tasks, function (searchStr, data, index) {
        let checked = $cb_visible_disabled_tasks.prop("checked");
        localStorage.setItem(cb_visible_disabled_tasks, checked);

        // Если задача не активная и флаг не убран
        if (!data.is_enabled && !checked) {
            return false;
        }
        return true;
    });

    $cb_visible_disabled_tasks.on('change', function (e) {
        table.draw();
    });
});
