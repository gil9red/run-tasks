$(function() {
    const tableId = "table-task-all-logs";

    // Отключение автообновления таблиц из base.js
    DATATABLES_AUTO_RELOAD_STOPPING.push(tableId);

    new DataTable(`#${tableId}`, {
        ajax: {
            url: `/api/task/${TASK_ID}/logs`,
            dataSrc: '',
        },
        rowId: 'id',
        columnDefs: [
            {
                targets: "_all",
                createdCell: function (td, cellData, rowData, row, col) {
                    // Окрашивание текста строки для ошибок
                    if (rowData.kind == 'err') {
                        $(td).addClass('text-danger');
                    }
                }
            }
        ],
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
