;(function () {

    var Main = {
        mixins: [BaseMixin],
        data: function () {
            classes: []
        },
        created: function () {

            var app = this;
            axios.get(GlobalCodesUrl, {

                params: {
                    class_name: "班次"
                }
            }).then(function (response) {

                app.classes = response.data.results;
                console.log(app.classes)
            }).catch(function (error) {

            })
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount("#app")
})();