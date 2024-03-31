$(function() {
    new DataTable('#table-task-run-logs', {
        ajax: {
            url: `/api/task/${TASK_ID}/run/${TASK_RUN_SEQ}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            { data: 'id', title: 'Ид.', },
            { data: 'task_run', title: 'Запуск', },
            { data: 'kind', title: 'Тип', },
            { data: 'text', title: 'Текст', },
            { data: 'date', title: 'Дата', render: date_render, },
        ],
        order: [
            // Сортировка по возрастанию id
            [0, "asc"],
        ],
        language: LANG_DATATABLES,
    });
});
