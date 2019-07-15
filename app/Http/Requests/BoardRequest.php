<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use App\Enums\SubscriptionType;
use BenSampo\Enum\Rules\EnumValue;
use App\Enums\BoardType;

class BoardRequest extends FormRequest
{
    /**
     * Prepare the data for validation.
     *
     * @return void
     */
    protected function prepareForValidation()
    {
        $this->merge([
            'can_post' => intval($this->can_post),
            'tower_id' => $this->type == BoardType::TOWER ? $this->tower_id : null,
            'name' => // Replace spaces with hyphens, remove doubles and any other characters
                preg_replace(
                    "/[\s]+/",
                    '-',
                    preg_replace(
                        "/[^a-z0-9\-\ ]/",
                        '',
                        strtolower($this->readable_name)
                    )
                ),
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
            'name' => 'required|unique:boards,name,' . (isset($this->board) ? $this->board->id : -1) . ',id',
            'can_post' => ['required', new EnumValue(SubscriptionType::class)],
            'website_url' => 'nullable|url',
            'twitter_handle' => 'nullable|regex:/^[A-Za-z_]{1,15}$/i',
            'facebook_url' => 'nullable|regex:/^[A-Za-z0-9\.\-\/]+$/i',
            'latitude' => 'nullable|numeric|between:-90,90',
            'longitude' => 'nullable|numeric|between:-180,180',
        ];
    }

    public function messages()
    {
        return [
            'name.required' => 'Please enter the name of the board',
            'name.unique' => 'This board name is already taken',
            'website_url.url' => 'The website address is not valid - it should start http:// or https://',
            'twitter_handle.regex' => 'The Twitter handle should be only characters or underscores',
            'facebook_url.regex' => 'The Facebook address is not valid - just include the part after facebook.com/',
        ];
    }
}
