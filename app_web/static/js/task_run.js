$(function() {
    new DataTable('#table-task-run-logs', {
        ajax: {
            url: `/api/task/${TASK_ID}/run/${TASK_RUN_SEQ}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
        columns: [
            {
                data: null, // Явное указание, что тут нет источника данных
                render: () => null,
                orderable: false,
                title: getTableHeaderTitleWithMenu(), // TODO: Перенести кнопку создания?
                width: '0px',
            },
            { data: 'id', title: 'Ид.', },
            { data: 'task_run', title: 'Запуск', },
            { data: 'kind', title: 'Тип', },
            { data: 'text', title: 'Текст', },
            { data: 'date', title: 'Дата', render: date_render, },
        ],
        order: [
            // Сортировка по возрастанию id
            [1, "asc"],
        ],
        ...COMMON_PROPS_DATA_TABLE,
    });
});
