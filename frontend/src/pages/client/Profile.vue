<template>


  <div class="grid">


    <div class="panel grid">


      <h3>{{ t("sections.profileDetails") }}</h3>


      <div class="field-group">
        <input v-model="firstName" :placeholder="t('placeholders.firstName')" />
      </div>
      <div class="field-group">
        <input v-model="lastName" :placeholder="t('placeholders.lastName')" />
      </div>
      <div class="field-group">
        <input v-model="email" :placeholder="t('placeholders.email')" />
      </div>
      <button @click="saveProfile">{{ t("buttons.save") }}</button>


      <p v-if="profileError" class="notice error">{{ profileError }}</p>
      <p v-if="profileMessage" class="notice success">{{ profileMessage }}</p>


    </div>
    <div class="panel">


      <h2>{{ t("titles.profile") }}</h2>


      <div class="list">


        <div class="list-item">


          <div>{{ t("labels.email") }}</div>


          <div>{{ user?.email }}</div>


        </div>


        <div class="list-item">


          <div>{{ t("labels.emailVerified") }}</div>


          <div>{{ user?.email_verified ? t("common.yes") : t("common.no") }}</div>


        </div>


        <div class="list-item">


          <div>{{ t("labels.phone") }}</div>


          <div>{{ user?.phone || "-" }}</div>


        </div>


        <div class="list-item">


          <div>{{ t("labels.phoneVerified") }}</div>


          <div>{{ user?.phone_verified ? t("common.yes") : t("common.no") }}</div>


        </div>


      </div>


    </div>


    <div class="panel grid">


      <h3>{{ t("sections.verifyEmail") }}</h3>


      <button class="ghost" @click="requestEmailCode">{{ t("buttons.requestEmailCode") }}</button>


      <div class="field-group">
        <input v-model="emailCode" :placeholder="t('placeholders.emailCode')" />
        <div class="field-help">Код из письма для подтверждения email.</div>
      </div>
      <button @click="confirmEmail">{{ t("buttons.confirm") }}</button>


      <p class="small">{{ emailMessage }}</p>


    </div>


    <div class="panel grid">


      <h3>{{ t("sections.bindPhone") }}</h3>


      <div class="field-group">
        <input v-model="phone" :placeholder="t('placeholders.phone')" />
        <div class="field-help">Номер телефона для привязки к аккаунту.</div>
      </div>
      <button class="ghost" @click="requestPhone">{{ t("buttons.requestOtp") }}</button>


      <div class="field-group">
        <input v-model="phoneCode" :placeholder="t('placeholders.phoneCode')" />
        <div class="field-help">Код из SMS для подтверждения телефона.</div>
      </div>
      <button @click="confirmPhone">{{ t("buttons.confirm") }}</button>


      <p class="small">{{ phoneMessage }}</p>


    </div>


    <div class="panel grid">


      <h3>{{ t("sections.changePassword") }}</h3>


      <div class="field-group">
        <input v-model="passwordCurrent" type="password" :placeholder="t('placeholders.currentPassword')" />
        <div class="field-help">Введите текущий пароль.</div>
      </div>
      <div class="field-group">
        <input v-model="passwordNew" type="password" :placeholder="t('placeholders.newPassword')" />
        <div class="field-help">Введите новый пароль.</div>
      </div>
      <button @click="changePassword">{{ t("buttons.changePassword") }}</button>


      <p class="small">{{ passwordMessage }}</p>


    </div>


  </div>


</template>





<script setup lang="ts">


import { onMounted, ref } from "vue";


import { useRoute } from "vue-router";


import { useI18n } from "vue-i18n";


import { apiFetch } from "../../api";


import { useAuthStore } from "../../stores/auth";





const route = useRoute();


const { t } = useI18n();


const auth = useAuthStore();


const tenant = route.params.tenant as string;


const user = ref(auth.user);


const emailCode = ref("");


const emailMessage = ref("");


const phone = ref("");


const phoneCode = ref("");


const phoneMessage = ref("");


const firstName = ref("");


const lastName = ref("");


const email = ref("");


const profileMessage = ref("");


const profileError = ref("");


const passwordCurrent = ref("");
const passwordNew = ref("");


const passwordMessage = ref("");





async function requestEmailCode() {


  emailMessage.value = "";


  await apiFetch(`/t/${tenant}/auth/email/request-code`, {


    method: "POST",


    headers: { "Content-Type": "application/json" },


    body: JSON.stringify({ email: user?.email }),


  });


  emailMessage.value = t("messages.codeSent");


}





async function confirmEmail() {


  emailMessage.value = "";


  const data = await apiFetch(`/t/${tenant}/auth/email/confirm`, {
    method: "POST",


    headers: { "Content-Type": "application/json" },


    body: JSON.stringify({ email: user?.email, code: emailCode.value }),


  });


  if (data?.user && data?.tokens) {
    user.value = data.user;
    auth.setAuth({ user: data.user, tokens: data.tokens, tenant });
  }

  emailMessage.value = t("messages.emailVerified");


}





async function requestPhone() {


  phoneMessage.value = "";


  const data = await apiFetch(`/t/${tenant}/auth/phone/request`, {


    method: "POST",


    headers: {


      "Content-Type": "application/json",


      Authorization: `Bearer ${auth.tokens?.access}`,


    },


    body: JSON.stringify({ phone: phone.value }),


  });


  phoneMessage.value = data.otp ? `${t("labels.otp")}: ${data.otp}` : t("messages.otpSent");


}





async function confirmPhone() {


  phoneMessage.value = "";


  await apiFetch(`/t/${tenant}/auth/phone/confirm`, {


    method: "POST",


    headers: {


      "Content-Type": "application/json",


      Authorization: `Bearer ${auth.tokens?.access}`,


    },


    body: JSON.stringify({ code: phoneCode.value }),


  });


  const me = await apiFetch(`/t/${tenant}/client/me`, {
    headers: { Authorization: `Bearer ${auth.tokens?.access}` },
  });
  user.value = me;
  auth.setAuth({ user: me, tokens: auth.tokens!, tenant });
  phoneMessage.value = t("messages.phoneVerified");


}





async function saveProfile() {


  profileMessage.value = "";


  profileError.value = "";


  if (!firstName.value.trim() || !lastName.value.trim()) {
    profileError.value = t("messages.profileRequired");
    return;
  }
  if (!email.value.trim()) {
    profileError.value = t("messages.emailRequired");
    return;
  }
  const data = await apiFetch(`/t/${tenant}/client/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${auth.tokens?.access}`,
    },
    body: JSON.stringify({ first_name: firstName.value, last_name: lastName.value, email: email.value }),
  });
  user.value = data.user;
  auth.setAuth({ user: data.user, tokens: auth.tokens!, tenant });
  profileMessage.value = t("messages.saved");
}


async function changePassword() {
  passwordMessage.value = "";


  await apiFetch(`/t/${tenant}/client/profile/password`, {


    method: "POST",


    headers: {


      "Content-Type": "application/json",


      Authorization: `Bearer ${auth.tokens?.access}`,


    },


    body: JSON.stringify({ current_password: passwordCurrent.value, new_password: passwordNew.value }),


  });


  passwordMessage.value = t("messages.passwordChanged");


}





onMounted(async () => {


  const data = await apiFetch(`/t/${tenant}/client/me`, {


    headers: { Authorization: `Bearer ${auth.tokens?.access}` },


  });


  user.value = data;


  phone.value = data.phone || "";


  firstName.value = data.first_name || "";


  lastName.value = data.last_name || "";


  email.value = data.email || "";


  email.value = data.email || "";
});
</script>


