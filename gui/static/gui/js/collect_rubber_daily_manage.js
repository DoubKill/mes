;(function () {

    var Main = {

        mixins: [BaseMixin],
        data: function () {
            return {

                dialogRubberBarCodeInfoVisible: false
                // tableDataUrl: PalletFeedBacksUrl,
            }
        },
        methods:{

           check_() {

               this.dialogRubberBarCodeInfoVisible = true
           }
        }
    };
    var Ctor = Vue.extend(Main);
    new Ctor().$mount('#app')

})();