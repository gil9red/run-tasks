function process_cron() {
    let $cron_result_error = $(".cron-result-error");
    let $cron_result = $("#next-dates");

    $cron_result_error.text("");
    $cron_result.text("");

    let cron = $.trim($("#cron").val());
    if (!cron) {
        return;
    }

    $.ajax({
        url: "/api/cron/get-next-dates",
        method: "GET",
        data: {
            cron: cron,
            number: 7,
        },
        contentType: "application/json; charset=utf-8",
        dataType: "json",  // Тип данных загружаемых с сервера
        success: function(data) {
            let ok = data.status == 'ok';
            if (ok) {
                let items = [];
                for (let item of data.result) {
                    let date_str = get_date_from_utc(item.date);
                    items.push(
                        `<div>${date_str}</div>`
                    );
                }
                let result = items.join("");
                $cron_result.html(result);
            } else {
                $cron_result_error.text(data.text);
            }
        },
        error: data => on_ajax_error(data, "при запросе следующих дат")
    });
}


$(function() {
    process_cron();
    $("#cron").on("input change", () => process_cron());

    $('[type="checkbox"][data-bs-toggle="collapse"][data-bs-target]').each(
        (i, item) => {
            let $item = $(item);

            if ($item.prop("checked")) {
                bootstrap.Collapse
                .getOrCreateInstance(
                    $item.data("bs-target")
                )
                .show();
            }
        }
    );

    $(".cron-examples code").click(function() {
        $("#cron").val(
            $(this).text()
        ).change();
    });
});
