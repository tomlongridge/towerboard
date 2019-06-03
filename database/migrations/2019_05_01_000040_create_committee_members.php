<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;

use App\Enums\UserContactVisibility;

class CreateCommitteeMembers extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('committee_members', function (Blueprint $table) {
            $table->bigIncrements('id');
            $table->unsignedBigInteger('user_id');
            $table->string('role');
            $table->unsignedTinyInteger('visibility_name')->default(UserContactVisibility::NONE);
            $table->unsignedTinyInteger('visibility_email')->default(UserContactVisibility::NONE);
            $table->unsignedTinyInteger('visibility_phone')->default(UserContactVisibility::NONE);
            $table->unsignedTinyInteger('visibility_address')->default(UserContactVisibility::NONE);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('committee_members');
    }
}
