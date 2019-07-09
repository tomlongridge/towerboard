<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

use BenSampo\Enum\Rules\EnumValue;
use App\Enums\SubscriptionType;
use Carbon\Carbon;

class NoticeRequest extends FormRequest
{
    /**
     * Prepare the data for validation.
     *
     * @return void
     */
    protected function prepareForValidation()
    {
        $this->merge([
            'distribution' => intval($this->distribution),
            'expires' => isset($this->expires) ? Carbon::createFromFormat('d/m/Y', $this->expires) : null,
        ]);
    }

    /**
     * Get the validation rules that apply to the request.
     *
     * @return array
     */
    public function rules()
    {
        return [
            'title' => 'required',
            'body' => 'required',
            'distribution' => ['required', new EnumValue(SubscriptionType::class)],
            'reply_to' => 'sometimes',
        ];
    }
}
