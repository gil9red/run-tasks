function get_cron() {
    return $.trim($("#cron").val());
}


function process_cron() {
    let $cron_result_error = $(".cron-result-error");
    let $cron_result = $("#next-dates");

    $cron_result_error.text("");
    $cron_result.text("");

    let cron = get_cron();
    if (!cron) {
        return;
    }

    $.ajax({
        url: "/api/cron/get-next-dates",
        method: "GET",
        data: {
            cron: cron,
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


function process_description() {
    let $description = $("#description");
    let $description_preview = $("#description-preview");

    $description_preview.html($description.val());
}


$(function() {
    process_cron();
    $("#cron").on("input change", () => process_cron());

    process_description();
    $("#description").on("input change", () => process_description());

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

    $("form").submit(function() {
        let thisForm = this;
        let $this = $(this);

        let url = $this.attr("action");
        let method = $this.attr("method");
        if (method === undefined) {
            method = "get";
        }

        let data = convertFormToJSON(this);

        // Чекбоксы при убранном флаге не добавляются в значение
        // и при установленном флаге будет значение "on"
        // Поэтому, нужно вручную это сделать
        $this.find("input[type=checkbox]").each((i, obj) => {
            let $obj = $(obj);
            data[$obj.attr("name")] = $obj.prop("checked");
        });

        $.ajax({
            url: url,
            method: method,  // HTTP метод, по умолчанию GET
            data: JSON.stringify(data),
            contentType: "application/json; charset=utf-8",
            dataType: "json",  // Тип данных загружаемых с сервера
            success: function(data) {
                on_ajax_success(
                    data,
                    null,
                    (css_selector_table, rs) => {
                        window.location.href = `/task/${rs.result[0].id}`;
                    }
                );

                // Очищение полей формы
                thisForm.reset();
            },
            error: data => on_ajax_error(data), // TODO: заполнять reason в on_ajax_error
        });

        return false;
    });
});
